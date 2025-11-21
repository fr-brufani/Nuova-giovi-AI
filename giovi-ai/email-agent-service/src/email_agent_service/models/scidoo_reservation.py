"""Modelli dati per Scidoo API."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ScidooCustomer:
    """Informazioni cliente dalla prenotazione Scidoo."""
    
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """Restituisce nome completo."""
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else "Unknown"
    
    @property
    def name(self) -> str:
        """Alias per full_name."""
        return self.full_name


@dataclass
class ScidooGuest:
    """Dettaglio ospite dalla prenotazione Scidoo."""
    
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    guest_type_id: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """Restituisce nome completo."""
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else "Unknown"


@dataclass
class ScidooReservation:
    """Rappresenta una prenotazione dalla Scidoo API."""
    
    id: str  # Numero prenotazione
    internal_id: str  # ID interno Scidoo
    room_type_id: str  # ID tipo alloggio
    checkin_date: datetime
    checkout_date: datetime
    status: str  # Stato prenotazione
    guest_count: int  # Numero totale ospiti
    customer: ScidooCustomer
    guests: List[ScidooGuest] = field(default_factory=list)
    creation: Optional[datetime] = None  # Data creazione prenotazione
    total_price: Optional[float] = None
    currency: Optional[str] = None
    
    @property
    def adults(self) -> int:
        """Calcola numero adulti dai guest."""
        # Se non ci sono guest dettagliati, usa guest_count
        if not self.guests:
            return self.guest_count
        
        # Conta adulti (age >= 14 o age None/assente)
        # Gestisce age come int, stringa o None in modo robusto
        adults_count = 0
        for g in self.guests:
            if g.age is None:
                # Se age non è specificato, assumiamo adulto
                adults_count += 1
            else:
                # Converti age a int se necessario
                try:
                    age_int = int(g.age) if not isinstance(g.age, int) else g.age
                    if age_int >= 14:
                        adults_count += 1
                except (ValueError, TypeError):
                    # Se age non è convertibile, assumiamo adulto
                    adults_count += 1
        
        return adults_count if adults_count > 0 else self.guest_count
    
    @property
    def children(self) -> int:
        """Calcola numero bambini dai guest."""
        if not self.guests:
            return 0
        
        # Conta bambini (age < 14)
        # Gestisce age come int, stringa o None in modo robusto
        children_count = 0
        for g in self.guests:
            if g.age is not None:
                try:
                    age_int = int(g.age) if not isinstance(g.age, int) else g.age
                    if age_int < 14:
                        children_count += 1
                except (ValueError, TypeError):
                    # Se age non è convertibile, skip
                    pass
        
        return children_count
    
    @property
    def reservation_id(self) -> str:
        """Alias per internal_id per compatibilità con altri modelli."""
        return self.internal_id

