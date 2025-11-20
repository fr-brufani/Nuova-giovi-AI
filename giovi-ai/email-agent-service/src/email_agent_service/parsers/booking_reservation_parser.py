"""Parser per XML OTA Booking.com Reservation API."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from xml.etree import ElementTree as ET

from ..models.booking_reservation import (
    BookingGuestInfo,
    BookingPaymentInfo,
    BookingReservation,
)

logger = logging.getLogger(__name__)

# Namespace OTA XML
OTA_NS = "{http://www.opentravel.org/OTA/2003/05}"


class BookingReservationParserError(Exception):
    """Eccezione per errori nel parsing XML OTA."""

    pass


def _get_element_text(element: Optional[ET.Element], default: str = "") -> str:
    """Estrae testo da elemento XML, con default se None."""
    if element is None:
        return default
    return (element.text or "").strip()


def _get_element_attr(element: Optional[ET.Element], attr: str, default: str = "") -> str:
    """Estrae attributo da elemento XML, con default se None."""
    if element is None:
        return default
    return element.get(attr, default)


def _parse_amount(
    element: Optional[ET.Element], amount_attr: str = "AmountBeforeTax", default: float = 0.0
) -> float:
    """
    Estrae amount da elemento Total XML.
    
    Nota: Secondo documentazione Booking.com OTA XML, Amount è già il valore finale
    (es. Amount="500" con DecimalPlaces="2" significa 500.00, non 5.00).
    DecimalPlaces indica solo quanti decimali mostrare, non un divisore.
    """
    if element is None:
        return default
    
    amount_str = element.get(amount_attr) or element.get("AmountAfterTax") or "0"
    
    try:
        # Amount è già il valore finale, non va diviso per DecimalPlaces
        return float(Decimal(amount_str))
    except (ValueError, TypeError):
        logger.warning(f"Impossibile parsare amount '{amount_str}'")
        return default


def _parse_datetime(datetime_str: str) -> Optional[datetime]:
    """Parsea datetime da stringa ISO format."""
    if not datetime_str:
        return None
    try:
        # Prova vari formati comuni
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S+00:00",
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        # Fallback a dateutil se disponibile
        from dateutil import parser as date_parser
        return date_parser.parse(datetime_str)
    except Exception as e:
        logger.warning(f"Impossibile parsare datetime '{datetime_str}': {e}")
        return None


def _extract_reservation_id(res_global_info: ET.Element) -> str:
    """Estrae reservation_id da ResGlobalInfo."""
    hotel_res_ids = res_global_info.find(f".//{OTA_NS}HotelReservationIDs")
    if hotel_res_ids is None:
        raise BookingReservationParserError("HotelReservationIDs non trovato in ResGlobalInfo")
    
    hotel_res_id = hotel_res_ids.find(f"{OTA_NS}HotelReservationID")
    if hotel_res_id is None:
        raise BookingReservationParserError("HotelReservationID non trovato")
    
    res_id_value = hotel_res_id.get("ResID_Value")
    if not res_id_value:
        raise BookingReservationParserError("ResID_Value vuoto o mancante")
    
    return res_id_value


def _extract_property_id(room_stay: ET.Element) -> str:
    """Estrae property_id da RoomStay."""
    basic_property = room_stay.find(f".//{OTA_NS}BasicPropertyInfo")
    if basic_property is None:
        raise BookingReservationParserError("BasicPropertyInfo non trovato in RoomStay")
    
    hotel_code = basic_property.get("HotelCode")
    if not hotel_code:
        raise BookingReservationParserError("HotelCode vuoto o mancante")
    
    return hotel_code


def _extract_dates(room_stay: ET.Element) -> tuple[Optional[datetime], Optional[datetime]]:
    """Estrae check_in e check_out da RoomStay."""
    check_in = None
    check_out = None
    
    # Check-in: prima RoomRate EffectiveDate
    room_rate = room_stay.find(f".//{OTA_NS}RoomRate")
    if room_rate is not None:
        effective_date = room_rate.get("EffectiveDate")
        if effective_date:
            check_in = _parse_datetime(effective_date)
    
    # Check-out: calcolato da numero notti (se disponibile) o cercato in altri campi
    # Per ora usiamo solo check-in e assumiamo che sia una notte
    # TODO: Migliorare estrazione check-out se disponibile in XML
    
    # Se non trovato, cerca in RoomRates per trovare l'ultima data
    room_rates = room_stay.findall(f".//{OTA_NS}RoomRate")
    if len(room_rates) > 0:
        # Prima data (check-in)
        first_date = room_rates[0].get("EffectiveDate")
        if first_date:
            check_in = _parse_datetime(first_date)
        
        # Ultima data + 1 giorno (check-out approssimativo)
        # Nota: L'XML OTA può avere multiple RoomRate per più notti
        if len(room_rates) > 1:
            last_date = room_rates[-1].get("EffectiveDate")
            if last_date:
                last_dt = _parse_datetime(last_date)
                if last_dt:
                    from datetime import timedelta
                    check_out = last_dt + timedelta(days=1)
        elif check_in:
            # Default: 1 notte se non specificato
            from datetime import timedelta
            check_out = check_in + timedelta(days=1)
    
    return check_in, check_out


def _extract_guest_info(res_global_info: ET.Element) -> BookingGuestInfo:
    """Estrae informazioni guest/booker da ResGlobalInfo."""
    profiles = res_global_info.find(f".//{OTA_NS}Profiles")
    if profiles is None:
        raise BookingReservationParserError("Profiles non trovato in ResGlobalInfo")
    
    profile_info = profiles.find(f"{OTA_NS}ProfileInfo")
    if profile_info is None:
        raise BookingReservationParserError("ProfileInfo non trovato")
    
    customer = profile_info.find(f".//{OTA_NS}Customer")
    if customer is None:
        raise BookingReservationParserError("Customer non trovato in Profile")
    
    # Nome
    person_name = customer.find(f"{OTA_NS}PersonName")
    given_name = ""
    surname = ""
    full_name = ""
    
    if person_name is not None:
        given_name_elem = person_name.find(f"{OTA_NS}GivenName")
        surname_elem = person_name.find(f"{OTA_NS}Surname")
        given_name = _get_element_text(given_name_elem)
        surname = _get_element_text(surname_elem)
        full_name = f"{given_name} {surname}".strip() or surname or given_name
    
    # Email
    email_elem = customer.find(f"{OTA_NS}Email")
    email = _get_element_text(email_elem)
    
    # Telefono
    phone_elem = customer.find(f"{OTA_NS}Telephone")
    phone = phone_elem.get("PhoneNumber") if phone_elem is not None else None
    
    if not email:
        raise BookingReservationParserError("Email guest non trovata")
    
    return BookingGuestInfo(
        name=full_name or email.split("@")[0],  # Fallback a parte locale email
        email=email,
        phone=phone,
        surname=surname if surname else None,
        given_name=given_name if given_name else None,
    )


def _extract_guest_counts(room_stay: ET.Element) -> tuple[int, int]:
    """Estrae numero adults e children da RoomStay."""
    adults = 2  # Default
    children = 0
    
    guest_counts = room_stay.find(f".//{OTA_NS}GuestCounts")
    if guest_counts is not None:
        guest_count_elems = guest_counts.findall(f"{OTA_NS}GuestCount")
        for gc in guest_count_elems:
            age_qualifying_code = gc.get("AgeQualifyingCode")
            count = int(gc.get("Count", "0"))
            
            if age_qualifying_code == "10":  # Adult
                adults = count
            elif age_qualifying_code == "8":  # Child
                children = count
    
    return adults, children


def _extract_totals(res_global_info: ET.Element) -> tuple[float, str]:
    """Estrae total amount e currency da ResGlobalInfo."""
    total_elem = res_global_info.find(f".//{OTA_NS}Total")
    if total_elem is None:
        logger.warning("Total non trovato in ResGlobalInfo, uso default")
        return 0.0, "EUR"
    
    amount = _parse_amount(total_elem)
    currency = total_elem.get("CurrencyCode", "EUR")
    
    return amount, currency


def _extract_payment_info(res_global_info: ET.Element) -> Optional[BookingPaymentInfo]:
    """Estrae informazioni pagamento/VCC da ResGlobalInfo."""
    guarantee = res_global_info.find(f".//{OTA_NS}Guarantee")
    if guarantee is None:
        return None
    
    guarantees_accepted = guarantee.find(f".//{OTA_NS}GuaranteesAccepted")
    if guarantees_accepted is None:
        return None
    
    guarantee_accepted = guarantees_accepted.find(f"{OTA_NS}GuaranteeAccepted")
    if guarantee_accepted is None:
        return None
    
    payment_card = guarantee_accepted.find(f".//{OTA_NS}PaymentCard")
    if payment_card is None:
        return None
    
    card_number = payment_card.get("CardNumber", "")
    card_holder_name = _get_element_text(payment_card.find(f"{OTA_NS}CardHolderName"))
    
    # Verifica se è VCC dummy (NOCCRESERVATION)
    is_payments_by_booking = card_holder_name.upper() != "NOCCRESERVATION"
    
    vcc_number = card_number if card_number and card_number != "0000000000000000" else None
    vcc_cvc = payment_card.get("SeriesCode") if is_payments_by_booking else None
    vcc_expiry_date = payment_card.get("ExpireDate") if is_payments_by_booking else None
    vcc_effective_date = _parse_datetime(payment_card.get("EffectiveDate", ""))
    
    # CurrentBalance per VCC
    # Nota: CurrentBalance è già il valore finale, non va diviso per DecimalPlaces
    current_balance_str = payment_card.get("CurrentBalance", "")
    vcc_current_balance = None
    if current_balance_str and current_balance_str != "0":
        try:
            vcc_current_balance = float(Decimal(current_balance_str))
        except (ValueError, TypeError):
            pass
    
    if not vcc_number:
        return None
    
    return BookingPaymentInfo(
        vcc_number=vcc_number,
        vcc_cvc=vcc_cvc,
        vcc_expiry_date=vcc_expiry_date,
        vcc_effective_date=vcc_effective_date,
        vcc_current_balance=vcc_current_balance,
        card_holder_name=card_holder_name if card_holder_name else None,
        is_payments_by_booking=is_payments_by_booking,
    )


def _extract_reservation_date(res_global_info: ET.Element) -> Optional[datetime]:
    """Estrae data creazione prenotazione da HotelReservationID."""
    hotel_res_ids = res_global_info.find(f".//{OTA_NS}HotelReservationIDs")
    if hotel_res_ids is None:
        return None
    
    hotel_res_id = hotel_res_ids.find(f"{OTA_NS}HotelReservationID")
    if hotel_res_id is None:
        return None
    
    res_id_date = hotel_res_id.get("ResID_Date")
    if res_id_date:
        return _parse_datetime(res_id_date)
    
    return None


def _extract_commission(room_stay: ET.Element) -> Optional[float]:
    """Estrae commission amount da RoomStay."""
    rate_plan = room_stay.find(f".//{OTA_NS}RatePlan")
    if rate_plan is None:
        return None
    
    commission = rate_plan.find(f".//{OTA_NS}Commission")
    if commission is None:
        return None
    
    commission_amount_elem = commission.find(f"{OTA_NS}CommissionPayableAmount")
    if commission_amount_elem is None:
        return None
    
    return _parse_amount(commission_amount_elem, amount_attr="Amount")


def _extract_special_requests(room_stay: ET.Element) -> List[str]:
    """Estrae special requests da RoomStay."""
    requests = []
    special_requests_elem = room_stay.find(f".//{OTA_NS}SpecialRequests")
    if special_requests_elem is not None:
        for sr in special_requests_elem.findall(f"{OTA_NS}SpecialRequest"):
            text_elem = sr.find(f"{OTA_NS}Text")
            if text_elem is not None and text_elem.text:
                requests.append(text_elem.text.strip())
    return requests


def parse_ota_modify_xml(xml_string: str) -> List[BookingReservation]:
    """
    Parsea XML OTA HotelResModifyNotif (modifiche/cancellazioni).
    
    Stessa struttura di parse_ota_xml ma per endpoint OTA_HotelResModifyNotif.
    
    Args:
        xml_string: XML string dalla Reservation API (modifiche)
        
    Returns:
        Lista di BookingReservation
        
    Raises:
        BookingReservationParserError: Se XML è invalido o mancano dati essenziali
    """
    # Il formato XML è identico a OTA_HotelResNotif, solo root element diverso
    # Sostituiamo HotelResModifies → HotelReservations per riutilizzare parsing
    xml_string_fixed = xml_string.replace("HotelResModifies", "HotelReservations")
    xml_string_fixed = xml_string_fixed.replace("HotelResModify", "HotelReservation")
    return parse_ota_xml(xml_string_fixed)


def parse_ota_xml(xml_string: str) -> List[BookingReservation]:
    """
    Parsea XML OTA Booking.com e restituisce lista di BookingReservation.
    
    Args:
        xml_string: XML string dalla Reservation API
        
    Returns:
        Lista di BookingReservation
        
    Raises:
        BookingReservationParserError: Se XML è invalido o mancano dati essenziali
    """
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        raise BookingReservationParserError(f"Errore parsing XML: {e}") from e
    
    # Trova HotelReservations
    hotel_reservations = root.find(f".//{OTA_NS}HotelReservations")
    if hotel_reservations is None:
        logger.warning("Nessuna HotelReservation trovata nell'XML")
        return []
    
    reservations = []
    
    for hotel_reservation in hotel_reservations.findall(f"{OTA_NS}HotelReservation"):
        try:
            res_global_info = hotel_reservation.find(f"{OTA_NS}ResGlobalInfo")
            if res_global_info is None:
                logger.warning("ResGlobalInfo non trovato, salto prenotazione")
                continue
            
            # Estrai dati comuni
            reservation_id = _extract_reservation_id(res_global_info)
            reservation_date = _extract_reservation_date(res_global_info)
            guest_info = _extract_guest_info(res_global_info)
            total_amount, currency = _extract_totals(res_global_info)
            payment_info = _extract_payment_info(res_global_info)
            
            # Processa ogni RoomStay (una prenotazione può avere più stanze)
            room_stays = hotel_reservation.find(f"{OTA_NS}RoomStays")
            if room_stays is None:
                logger.warning(f"Nessun RoomStay trovato per prenotazione {reservation_id}")
                continue
            
            for room_stay in room_stays.findall(f"{OTA_NS}RoomStay"):
                try:
                    property_id = _extract_property_id(room_stay)
                    check_in, check_out = _extract_dates(room_stay)
                    adults, children = _extract_guest_counts(room_stay)
                    commission_amount = _extract_commission(room_stay)
                    special_requests = _extract_special_requests(room_stay)
                    
                    # Estrai room type info (opzionale)
                    room_type = room_stay.find(f".//{OTA_NS}RoomType")
                    room_type_code = room_type.get("RoomTypeCode") if room_type is not None else None
                    room_type_name = None
                    if room_type is not None:
                        room_desc = room_type.find(f"{OTA_NS}RoomDescription")
                        if room_desc is not None:
                            room_type_name = room_desc.get("Name")
                    
                    # Estrai rate plan (opzionale)
                    room_rate = room_stay.find(f".//{OTA_NS}RoomRate")
                    rate_plan_code = room_rate.get("RatePlanCode") if room_rate is not None else None
                    
                    # Estrai meal plan (opzionale)
                    meal_plan = None
                    if room_type is not None:
                        room_desc = room_type.find(f"{OTA_NS}RoomDescription")
                        if room_desc is not None:
                            meal_plan_elem = room_desc.find(f"{OTA_NS}MealPlan")
                            meal_plan = _get_element_text(meal_plan_elem)
                    
                    # Estrai comments (opzionale)
                    comments = None
                    comments_elem = res_global_info.find(f".//{OTA_NS}Comments")
                    if comments_elem is not None:
                        comment_elem = comments_elem.find(f"{OTA_NS}Comment")
                        if comment_elem is not None:
                            comments = _get_element_text(comment_elem.find(f"{OTA_NS}Text"))
                    
                    if not check_in or not check_out:
                        logger.warning(
                            f"Date non valide per prenotazione {reservation_id}: check_in={check_in}, check_out={check_out}"
                        )
                        continue
                    
                    reservation = BookingReservation(
                        reservation_id=reservation_id,
                        property_id=property_id,
                        check_in=check_in,
                        check_out=check_out,
                        guest_info=guest_info,
                        adults=adults,
                        children=children,
                        total_amount=total_amount,
                        currency=currency,
                        room_type_code=room_type_code,
                        room_type_name=room_type_name,
                        rate_plan_code=rate_plan_code,
                        meal_plan=meal_plan,
                        commission_amount=commission_amount,
                        payment_info=payment_info,
                        special_requests=special_requests,
                        comments=comments,
                        reservation_date=reservation_date,
                    )
                    
                    reservations.append(reservation)
                    
                except Exception as e:
                    logger.error(f"Errore processando RoomStay per prenotazione {reservation_id}: {e}", exc_info=True)
                    continue
        
        except Exception as e:
            logger.error(f"Errore processando HotelReservation: {e}", exc_info=True)
            continue
    
    if not reservations:
        logger.warning("Nessuna prenotazione valida estratta dall'XML")
    
    return reservations

