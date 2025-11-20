"""Fixture con mock responses Booking.com API per testing."""

# Mock response per GET /messages/latest
MOCK_MESSAGES_LATEST_RESPONSE = {
    "meta": {"ruid": "UmFuZG9tSVYkc2RlIyh9YYuVGLmv13PUyJxscfB0hkeHNTLsLGWx80EBzv17yAX3aPO0RTlx5doV49/NRR4qak1qNsDGbilP"},
    "warnings": [],
    "data": {
        "messages": [
            {
                "message_id": "4ad42260-e0aa-11ea-b1cb-0975761ce091",
                "message_type": "free_text",
                "content": "Hello, I have a question about my reservation",
                "timestamp": "2025-01-15T10:00:00.270Z",
                "sender": {
                    "participant_id": "9f6be5fd-b3a8-5691-9cf9-9ab6c6217327",
                    "metadata": {
                        "participant_type": "GUEST",
                        "name": "Test Guest",
                    },
                },
                "conversation": {
                    "conversation_type": "reservation",
                    "conversation_id": "f3a9c29d-480d-5f5b-a6c0-65451e335353",
                    "conversation_reference": "3812391309",
                },
                "attachment_ids": [],
            }
        ],
        "ok": True,
        "number_of_messages": 1,
        "timestamp": "2025-01-15T10:00:00.270Z",
    },
    "errors": [],
}

# Mock response per GET /properties/{property_id}/conversations/type/reservation
MOCK_CONVERSATION_BY_RESERVATION_RESPONSE = {
    "meta": {"ruid": "UmFuZG9tSVYkc2RlIyh9YYX5KO46o0C5R5CiotKrM4awgb8DeWP40oDQG6OR6x4lvYqbLiGYUQHR5EgyMmTTT8xAnK2feAdc"},
    "warnings": [],
    "data": {
        "ok": "true",
        "conversation": {
            "conversation_id": "f3a9c29d-480d-5f5b-a6c0-65451e335353",
            "conversation_type": "reservation",
            "conversation_reference": "3812391309",
            "access": "read_write",
            "participants": [
                {
                    "participant_id": "9f6be5fd-b3a8-5691-9cf9-9ab6c6217327",
                    "metadata": {
                        "type": "guest",
                        "name": "Test Guest",
                    },
                },
                {
                    "participant_id": "mock-property-id",
                    "metadata": {
                        "type": "property",
                        "id": "8011855",
                    },
                },
            ],
            "messages": [],
        },
    },
    "errors": [],
}

# Mock XML response per GET /OTA_HotelResNotif
MOCK_OTA_XML_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<OTA_HotelResNotifRQ xmlns="http://www.opentravel.org/OTA/2003/05" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opentravel.org/OTA/2003/05 OTA_HotelResNotifRQ.xsd" TimeStamp="2025-01-15T10:00:00+00:00" Target="Production" Version="2.001">
    <HotelReservations>
        <HotelReservation>
            <RoomStays>
                <RoomStay IndexNumber="460">
                    <RoomTypes>
                        <RoomType RoomTypeCode="1296364403">
                            <RoomDescription Name="Deluxe Double Room - General">
                                <Text>This double room features a bathrobe, hot tub and game console.</Text>
                                <MealPlan>Breakfast is included in the room rate.</MealPlan>
                            </RoomDescription>
                        </RoomType>
                    </RoomTypes>
                    <RatePlans>
                        <RatePlan>
                            <Commission>
                                <CommissionPayableAmount Amount="50" DecimalPlaces="2" CurrencyCode="EUR"/>
                            </Commission>
                        </RatePlan>
                    </RatePlans>
                    <RoomRates>
                        <RoomRate EffectiveDate="2025-03-29" RatePlanCode="49111777">
                            <Rates>
                                <Rate>
                                    <Total AmountBeforeTax="500" CurrencyCode="EUR" DecimalPlaces="2"/>
                                </Rate>
                            </Rates>
                        </RoomRate>
                    </RoomRates>
                    <GuestCounts>
                        <GuestCount Count="2" AgeQualifyingCode="10"/>
                    </GuestCounts>
                    <BasicPropertyInfo HotelCode="8011855"/>
                </RoomStay>
            </RoomStays>
            <ResGlobalInfo>
                <HotelReservationIDs>
                    <HotelReservationID ResID_Value="4705950059" ResID_Date="2025-01-15T10:00:00"/>
                </HotelReservationIDs>
                <Profiles>
                    <ProfileInfo>
                        <Profile>
                            <Customer>
                                <PersonName>
                                    <GivenName>Test</GivenName>
                                    <Surname>Guest</Surname>
                                </PersonName>
                                <Telephone PhoneNumber="+39 333 1234567"/>
                                <Email>test.guest@example.com</Email>
                            </Customer>
                        </Profile>
                    </ProfileInfo>
                </Profiles>
                <Total AmountBeforeTax="500" CurrencyCode="EUR" DecimalPlaces="2"/>
            </ResGlobalInfo>
        </HotelReservation>
    </HotelReservations>
</OTA_HotelResNotifRQ>"""

# Mock XML response per POST /OTA_HotelResNotif (acknowledgement)
MOCK_OTA_ACK_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<OTA_HotelResNotifRS xmlns="http://www.opentravel.org/OTA/2003/05" TimeStamp="2025-01-15T10:00:01+00:00">
    <Success/>
</OTA_HotelResNotifRS>"""

