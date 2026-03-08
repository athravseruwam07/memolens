"""
Voice Query Service for MemoLens.
Processes voice queries, detects intent, and generates natural language responses.
"""

import re
from datetime import datetime, date
from typing import Optional
from uuid import UUID
from enum import Enum
from dataclasses import dataclass, field

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import ItemState, Event, DailyNote, Reminder, FamiliarPerson


class VoiceIntent(Enum):
    """Voice command intents."""
    FIND_ITEM = "find_item"
    IDENTIFY_PERSON = "identify_person"
    TODAY_REMINDERS = "today_reminders"
    MEDICATION = "medication"
    DAILY_SUMMARY = "daily_summary"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent detection."""
    intent: VoiceIntent
    entities: dict = field(default_factory=dict)
    confidence: float = 1.0


COMMON_ITEMS = [
    # === COCO Dataset Classes (YOLOv8 detectable) ===
    # People & Animals
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", 
    "truck", "boat", "traffic light", "fire hydrant", "stop sign", 
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", 
    "cow", "elephant", "bear", "zebra", "giraffe",
    
    # Accessories & Personal Items
    "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", 
    "skis", "snowboard", "sports ball", "kite", "baseball bat", 
    "baseball glove", "skateboard", "surfboard", "tennis racket",
    
    # Kitchen & Dining
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl",
    "banana", "apple", "sandwich", "orange", "broccoli", "carrot", 
    "hot dog", "pizza", "donut", "cake",
    
    # Furniture & Home
    "chair", "couch", "sofa", "potted plant", "bed", "dining table", 
    "table", "toilet", "tv", "television", "laptop", "mouse", 
    "remote", "keyboard", "cell phone", "microwave", "oven", 
    "toaster", "sink", "refrigerator", "fridge", "book", "clock", 
    "vase", "scissors", "teddy bear", "hair drier", "toothbrush",
    
    # === Common Household Items for Elderly/Dementia Patients ===
    # Electronics & Devices
    "phone", "mobile", "mobile phone", "cellphone", "smartphone",
    "iphone", "android", "samsung", "ipad", "tablet", "computer",
    "charger", "phone charger", "charging cable", "power bank",
    "headphones", "earbuds", "airpods", "earphones", "hearing aid",
    "hearing aids", "tv remote", "remote control", "controller",
    "radio", "alarm clock", "watch", "smartwatch", "fitbit",
    
    # Keys & Wallet
    "keys", "key", "car keys", "car key", "house keys", "house key",
    "keychain", "key ring", "key fob",
    "wallet", "purse", "handbag", "pocketbook", "billfold",
    "credit card", "debit card", "card", "cards", "id", "id card",
    "driver license", "drivers license", "license",
    "passport", "documents", "papers", "paperwork",
    
    # Eyewear
    "glasses", "eyeglasses", "spectacles", "specs", "reading glasses",
    "sunglasses", "shades", "contacts", "contact lenses", "lens case",
    
    # Medical & Health
    "medicine", "medication", "medications", "meds", "pills", "pill",
    "pill bottle", "pill box", "pillbox", "medicine bottle",
    "prescription", "prescriptions", "vitamins", "vitamin",
    "inhaler", "oxygen", "oxygen tank", "nebulizer",
    "blood pressure monitor", "glucose meter", "thermometer",
    "hearing aid", "hearing aids", "dentures", "teeth", "false teeth",
    "walker", "cane", "walking stick", "crutches", "crutch",
    "wheelchair", "rollator", "mobility aid",
    "bandage", "bandages", "band aid", "first aid kit",
    
    # Clothing & Accessories
    "shoes", "shoe", "slippers", "slipper", "sandals", "boots",
    "sneakers", "loafers", "flip flops",
    "coat", "jacket", "sweater", "cardigan", "hoodie", "vest",
    "hat", "cap", "beanie", "scarf", "scarves", "gloves", "mittens",
    "belt", "suspenders", "socks", "sock",
    "ring", "rings", "wedding ring", "jewelry", "jewellery",
    "necklace", "bracelet", "earrings", "brooch", "pin",
    
    # Bags & Carriers
    "bag", "bags", "tote", "tote bag", "shopping bag", "grocery bag",
    "messenger bag", "shoulder bag", "fanny pack", "waist bag",
    "briefcase", "laptop bag", "gym bag", "duffel bag", "duffle bag",
    "luggage", "carry on",
    
    # Reading & Writing
    "book", "books", "newspaper", "magazine", "magazines",
    "pen", "pens", "pencil", "pencils", "marker", "markers",
    "notebook", "notepad", "journal", "diary", "calendar", "planner",
    "letter", "letters", "mail", "envelope", "envelopes",
    
    # Kitchen Items
    "mug", "coffee mug", "tea cup", "glass", "glasses", "water bottle",
    "thermos", "flask", "pitcher", "jug",
    "plate", "plates", "dish", "dishes", "pan", "pot", "kettle",
    "coffee maker", "coffee machine", "blender", "mixer",
    
    # Living Room & Bedroom
    "blanket", "blankets", "throw", "quilt", "comforter",
    "pillow", "pillows", "cushion", "cushions",
    "towel", "towels", "washcloth", "bath towel",
    "sheet", "sheets", "bedding",
    
    # Bathroom
    "toothbrush", "toothpaste", "razor", "shaver", "comb", "brush",
    "hair brush", "soap", "shampoo", "lotion", "cream",
    
    # Photos & Memories
    "photo", "photos", "photograph", "photographs", "picture", "pictures",
    "photo album", "album", "frame", "picture frame",
    
    # Misc Common Items
    "flashlight", "torch", "batteries", "battery",
    "tissue", "tissues", "kleenex", "napkin", "napkins",
    "trash", "garbage", "recycle", "recycling",
    "fan", "heater", "lamp", "light", "bulb",
    "tool", "tools", "screwdriver", "hammer", "tape",
    "string", "rope", "wire", "cord", "cable",
    "box", "container", "bin", "basket", "bucket",
    "money", "cash", "coins", "change",
]

ITEM_PATTERNS = [
    (r"where (?:are|is|did|have) (?:my |the |i )?(?:put |leave |left |seen )?(?:my |the )?(.+?)(?:\?|$)", 1.0),
    (r"find (?:my |the )?(.+?)(?:\?|$)", 0.9),
    (r"(?:have you seen|did you see|seen) (?:my |the )?(.+?)(?:\?|$)", 0.9),
    (r"(?:where did i (?:put|leave|left)) (?:my |the )?(.+?)(?:\?|$)", 0.95),
    (r"(?:i lost|i can't find|can't find|cannot find|lost) (?:my |the )?(.+?)(?:\?|$)", 0.85),
    (r"(?:i )?(?:leave|left|put) (?:my |the )?(.+?)(?:\?|$)", 0.8),
    (r"(?:show me|locate|look for) (?:my |the )?(.+?)(?:\?|$)", 0.85),
    (r"(?:what happened to|where's|wheres) (?:my |the )?(.+?)(?:\?|$)", 0.9),
]

PERSON_PATTERNS = [
    (r"who is (?:this|that|he|she|the person|this person|that person)", 1.0),
    (r"who(?:'s| is) (?:this|that|here|there)", 1.0),
    (r"identify (?:this |that |the )?person", 0.95),
    (r"do i know (?:this |that |the )?(?:person|him|her|them)", 0.9),
    (r"who am i (?:looking at|seeing|talking to)", 0.95),
    (r"who(?:'s| is) (?:in front of me|standing|sitting)", 0.9),
    (r"(?:recognize|recognise) (?:this |that |the )?(?:person|face)", 0.9),
    (r"who is (?:he|she|it)", 0.9),
    (r"who are (?:they|you)", 0.85),
]

REMINDER_PATTERNS = [
    (r"what (?:do i|should i) (?:need to )?remember", 1.0),
    (r"(?:what are|tell me|what's|whats) (?:my |today'?s? )?reminders?", 1.0),
    (r"what(?:'s| is) (?:on )?(?:my |the )?schedule", 0.9),
    (r"what (?:do i have|am i doing|should i do) today", 0.9),
    (r"(?:any |my )?reminders?(?: for)?(?: today)?", 0.85),
    (r"remind(?:ers?)? (?:me|today|for today)", 0.85),
    (r"things to (?:remember|do)", 0.8),
    (r"to ?do (?:list|today)", 0.8),
]

MEDICATION_PATTERNS = [
    (r"(?:did i take|have i taken) (?:my )?(?:medication|medicine|pills|meds)", 1.0),
    (r"(?:when|what time) (?:should i|do i) take (?:my )?(?:medication|medicine|pills|meds)", 0.95),
    (r"(?:medication|medicine|pills|meds) (?:status|time|schedule|reminder)", 0.9),
    (r"(?:take|took) (?:my )?(?:medication|medicine|pills|meds)", 0.85),
]


def _extract_item_from_text(text: str) -> tuple[str | None, float]:
    """
    Extract item name from text using multiple strategies.
    Prefers longer matches to avoid partial matches (e.g., "credit card" over "car").
    
    Returns:
        Tuple of (item_name, confidence) or (None, 0) if not found
    """
    text_lower = text.lower().strip()
    
    # Sort items by length (descending) to match longer items first
    # This ensures "credit card" matches before "car", "pillow" before "pill"
    sorted_items = sorted(COMMON_ITEMS, key=len, reverse=True)
    
    for item in sorted_items:
        # Use word boundary matching to avoid partial matches within words
        # But also allow the item to match at the start/end of string
        pattern = r'(?:^|\s|,)' + re.escape(item) + r'(?:$|\s|,|\?|!|\.)'
        if re.search(pattern, text_lower):
            return item, 0.9
        # Also check for exact substring for compound items
        if ' ' in item and item in text_lower:
            return item, 0.9
    
    # Fallback: simple substring match for single-word items
    for item in sorted_items:
        if ' ' not in item and item in text_lower.split():
            return item, 0.85
    
    for pattern, confidence in ITEM_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            item = match.group(1).strip()
            item = re.sub(r"\s+", " ", item)
            item = re.sub(r"[^\w\s]", "", item)
            stop_words = {"the", "my", "a", "an", "i", "is", "are", "at", "in", "on", "to"}
            item = " ".join(w for w in item.split() if w not in stop_words)
            if item and len(item) > 1:
                return item, confidence
    
    return None, 0


def detect_voice_intent(text: str) -> IntentResult:
    """
    Detect the user's intent from voice input using fuzzy matching.
    
    This function uses multiple strategies:
    1. Direct keyword matching for common items
    2. Regex patterns for structured queries
    3. Fallback heuristics for natural language variations
    
    Args:
        text: Transcribed speech
        
    Returns:
        IntentResult with detected intent, entities, and confidence
    """
    text_lower = text.lower().strip()
    
    words = set(text_lower.split())
    
    medication_keywords = {"medication", "medicine", "pills", "meds", "prescription", "dosage"}
    if words & medication_keywords:
        for pattern, confidence in MEDICATION_PATTERNS:
            if re.search(pattern, text_lower):
                return IntentResult(
                    intent=VoiceIntent.MEDICATION,
                    confidence=confidence
                )
        return IntentResult(
            intent=VoiceIntent.MEDICATION,
            confidence=0.7
        )
    
    person_keywords = {"who", "person", "face", "recognize", "recognise", "identify"}
    person_context = {"this", "that", "he", "she", "they", "him", "her", "them"}
    if "who" in words or (words & person_keywords and words & person_context):
        for pattern, confidence in PERSON_PATTERNS:
            if re.search(pattern, text_lower):
                return IntentResult(
                    intent=VoiceIntent.IDENTIFY_PERSON,
                    confidence=confidence
                )
        if "who" in words:
            return IntentResult(
                intent=VoiceIntent.IDENTIFY_PERSON,
                confidence=0.75
            )
    
    reminder_keywords = {"reminder", "reminders", "remember", "schedule", "todo", "to-do"}
    if words & reminder_keywords:
        for pattern, confidence in REMINDER_PATTERNS:
            if re.search(pattern, text_lower):
                return IntentResult(
                    intent=VoiceIntent.TODAY_REMINDERS,
                    confidence=confidence
                )
        return IntentResult(
            intent=VoiceIntent.TODAY_REMINDERS,
            confidence=0.75
        )
    
    item_name, confidence = _extract_item_from_text(text)
    if item_name:
        return IntentResult(
            intent=VoiceIntent.FIND_ITEM,
            entities={"item": item_name},
            confidence=confidence
        )
    
    location_keywords = {"where", "find", "lost", "left", "leave", "put", "seen", "locate", "looking"}
    if words & location_keywords:
        for pattern, confidence in ITEM_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                item = match.group(1).strip()
                item = re.sub(r"\s+", " ", item)
                item = re.sub(r"[^\w\s]", "", item)
                stop_words = {"the", "my", "a", "an", "i", "is", "are", "at", "in", "on", "to"}
                item = " ".join(w for w in item.split() if w not in stop_words)
                if item and len(item) > 1:
                    return IntentResult(
                        intent=VoiceIntent.FIND_ITEM,
                        entities={"item": item},
                        confidence=confidence
                    )
        
        remaining_words = words - location_keywords - {"my", "the", "a", "an", "i", "did", "do", "have"}
        if remaining_words:
            potential_item = " ".join(w for w in text_lower.split() 
                                      if w in remaining_words and len(w) > 2)
            if potential_item:
                return IntentResult(
                    intent=VoiceIntent.FIND_ITEM,
                    entities={"item": potential_item},
                    confidence=0.6
                )

    if any(kw in text_lower for kw in ["today", "schedule", "plan", "day"]):
        return IntentResult(
            intent=VoiceIntent.DAILY_SUMMARY,
            confidence=0.7
        )

    return IntentResult(intent=VoiceIntent.UNKNOWN)


def _format_time_ago(dt: datetime) -> str:
    """Format a datetime as a human-readable time ago string."""
    # Handle timezone-aware and naive datetimes
    if dt.tzinfo is not None:
        from datetime import timezone
        now = datetime.now(timezone.utc)
    else:
        now = datetime.utcnow()
    
    # Make both naive for comparison if needed
    if dt.tzinfo is not None and now.tzinfo is None:
        dt = dt.replace(tzinfo=None)
    elif dt.tzinfo is None and now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(seconds / 86400)
    return f"{days} day{'s' if days != 1 else ''} ago"


# Map user-friendly item names to YOLO-detectable items
# This allows queries like "water bottle" to match "bottle" in the database
ITEM_SEARCH_ALIASES = {
    # Bottle variations
    "water bottle": ["bottle", "water bottle"],
    "water": ["bottle", "cup"],
    "drink": ["bottle", "cup"],
    "beverage": ["bottle", "cup"],
    
    # Phone variations  
    "cell phone": ["phone", "cell phone"],
    "mobile phone": ["phone", "mobile phone"],
    "cellphone": ["phone"],
    "smartphone": ["phone"],
    "iphone": ["phone"],
    "android": ["phone"],
    "mobile": ["phone"],
    
    # Earbuds/headphones (YOLO can't detect these, but we can try)
    "airpods": ["airpods", "earbuds", "headphones"],
    "earbuds": ["earbuds", "airpods", "headphones"],
    "headphones": ["headphones", "earbuds", "airpods"],
    "earphones": ["earphones", "earbuds", "headphones"],
    
    # Keys (YOLO can't detect keys, but we track them)
    "keys": ["keys", "key"],
    "car keys": ["keys", "car keys"],
    "house keys": ["keys", "house keys"],
    
    # Glasses
    "glasses": ["glasses", "eyeglasses", "spectacles"],
    "eyeglasses": ["glasses", "eyeglasses"],
    "spectacles": ["glasses", "spectacles"],
    "sunglasses": ["sunglasses", "glasses"],
    "reading glasses": ["glasses", "reading glasses"],
    
    # Wallet/purse
    "wallet": ["wallet", "handbag", "purse"],
    "purse": ["purse", "handbag", "wallet"],
    "handbag": ["handbag", "purse", "wallet", "backpack"],
    
    # Remote
    "remote": ["remote", "tv remote", "remote control"],
    "tv remote": ["remote", "tv remote"],
    "remote control": ["remote", "remote control"],
    
    # Laptop/computer
    "computer": ["laptop", "computer"],
    "notebook": ["laptop", "notebook"],
    
    # Cup/mug
    "mug": ["cup", "mug"],
    "coffee cup": ["cup", "mug"],
    "tea cup": ["cup", "mug"],
    "glass": ["cup", "wine glass", "glass"],
    
    # TV
    "television": ["tv", "television"],
    "tv": ["tv", "television"],
    
    # Medication
    "medication": ["medication", "medicine", "pills", "pill bottle"],
    "medicine": ["medication", "medicine", "pills"],
    "pills": ["medication", "pills", "pill bottle"],
    "vitamins": ["medication", "vitamins"],
    
    # Furniture
    "sofa": ["couch", "sofa"],
    "couch": ["couch", "sofa"],
}


def _get_search_terms(item_name: str) -> list[str]:
    """Get all search terms for an item, including aliases."""
    item_lower = item_name.lower().strip()
    
    # Check if there's an alias mapping
    if item_lower in ITEM_SEARCH_ALIASES:
        return ITEM_SEARCH_ALIASES[item_lower]
    
    # Return the original term
    return [item_lower]


async def get_item_location_response(
    db: AsyncSession,
    patient_id: UUID,
    item_name: Optional[str] = None
) -> dict:
    """
    Get a voice-friendly response about item locations.
    Uses fuzzy matching to find items (e.g., "water bottle" matches "bottle").
    
    Args:
        db: Database session
        patient_id: Patient UUID
        item_name: Specific item to look for (optional)
        
    Returns:
        Response dict with 'type' and 'message'
    """
    from sqlalchemy import or_
    
    query = select(ItemState).where(ItemState.patient_id == patient_id)

    if item_name:
        # Get all search terms including aliases
        search_terms = _get_search_terms(item_name)
        
        # Build OR conditions for all search terms
        conditions = [ItemState.item_name.ilike(f"%{term}%") for term in search_terms]
        query = query.where(or_(*conditions))

    query = query.order_by(desc(ItemState.last_seen_at)).limit(5)
    result = await db.execute(query)
    items = result.scalars().all()

    if not items:
        if item_name:
            return {
                "type": "item_location",
                "message": f"I don't have any record of your {item_name}. I'll keep an eye out for it.",
                "results": []
            }
        return {
            "type": "item_location",
            "message": "I haven't tracked any items recently.",
            "results": []
        }

    if item_name and len(items) == 1:
        item = items[0]
        time_ago = _format_time_ago(item.last_seen_at) if item.last_seen_at else None
        room = item.last_seen_room or "an unknown location"

        if time_ago:
            message = f"Your {item.item_name} were last seen in the {room} {time_ago}."
        else:
            message = f"Your {item.item_name} were last seen in the {room}."

        return {
            "type": "item_location",
            "message": message,
            "results": [{
                "item": item.item_name,
                "room": item.last_seen_room,
                "last_seen_at": item.last_seen_at.isoformat() if item.last_seen_at else None,
                "confidence": item.confidence
            }]
        }

    messages = []
    results = []
    for item in items[:3]:
        time_ago = _format_time_ago(item.last_seen_at) if item.last_seen_at else None
        room = item.last_seen_room or "an unknown location"

        if time_ago:
            messages.append(f"Your {item.item_name} in the {room} {time_ago}")
        else:
            messages.append(f"Your {item.item_name} in the {room}")

        results.append({
            "item": item.item_name,
            "room": item.last_seen_room,
            "last_seen_at": item.last_seen_at.isoformat() if item.last_seen_at else None,
            "confidence": item.confidence
        })

    return {
        "type": "item_location",
        "message": "Here's what I know: " + ". ".join(messages) + ".",
        "results": results
    }


async def get_last_recognized_person(db: AsyncSession, patient_id: UUID) -> dict:
    """
    Get information about the last recognized person.
    
    Args:
        db: Database session
        patient_id: Patient UUID
        
    Returns:
        Response dict with person info
    """
    result = await db.execute(
        select(Event)
        .where(Event.patient_id == patient_id, Event.type == "face_recognized")
        .order_by(desc(Event.occurred_at))
        .limit(1)
    )
    event = result.scalar_one_or_none()

    if not event or not event.payload:
        return {
            "type": "person_recognized",
            "message": "I haven't recognized anyone recently. Let me keep watching.",
            "results": None
        }

    person_id = event.payload.get("person_id")
    name = event.payload.get("name", "someone")

    person_result = await db.execute(
        select(FamiliarPerson).where(FamiliarPerson.id == person_id)
    )
    person = person_result.scalar_one_or_none()

    if person:
        relationship = person.relationship
        conversation_prompt = person.conversation_prompt

        if relationship:
            message = f"This is {name}, your {relationship}."
        else:
            message = f"This is {name}."

        if conversation_prompt:
            message += f" {conversation_prompt}"

        return {
            "type": "person_recognized",
            "message": message,
            "results": {
                "person_id": str(person.id),
                "name": person.name,
                "relationship": person.relationship,
                "notes": person.notes,
                "conversation_prompt": person.conversation_prompt
            }
        }

    return {
        "type": "person_recognized",
        "message": f"The last person I saw was {name}.",
        "results": {"name": name}
    }


async def get_today_reminders(db: AsyncSession, patient_id: UUID) -> dict:
    """
    Get today's reminders for the patient.
    
    Args:
        db: Database session
        patient_id: Patient UUID
        
    Returns:
        Response dict with reminders
    """
    result = await db.execute(
        select(Reminder).where(
            Reminder.patient_id == patient_id,
            Reminder.active == True
        )
    )
    reminders = result.scalars().all()

    if not reminders:
        return {
            "type": "reminders",
            "message": "You don't have any active reminders right now.",
            "results": []
        }

    messages = [f"You have {len(reminders)} reminder{'s' if len(reminders) != 1 else ''}. "]

    for i, reminder in enumerate(reminders[:5], 1):
        messages.append(f"{reminder.message}.")

    return {
        "type": "reminders",
        "message": " ".join(messages),
        "results": [
            {"id": str(r.id), "message": r.message, "type": r.type}
            for r in reminders
        ]
    }


async def get_medication_status(db: AsyncSession, patient_id: UUID) -> dict:
    """
    Get medication-related information.
    
    Args:
        db: Database session
        patient_id: Patient UUID
        
    Returns:
        Response dict with medication info
    """
    item_result = await db.execute(
        select(ItemState).where(
            ItemState.patient_id == patient_id,
            ItemState.item_name.ilike("%medication%") | ItemState.item_name.ilike("%pill%")
        )
    )
    items = item_result.scalars().all()

    reminder_result = await db.execute(
        select(Reminder).where(
            Reminder.patient_id == patient_id,
            Reminder.active == True
        )
    )
    reminders = reminder_result.scalars().all()
    med_reminders = [
        r for r in reminders
        if any(kw in (r.message or "").lower() for kw in ["med", "pill", "medicine"])
    ]

    messages = []

    if items:
        item = items[0]
        room = item.last_seen_room or "unknown location"
        messages.append(f"Your medication was last seen in the {room}.")

    if med_reminders:
        messages.append(f"You have {len(med_reminders)} medication reminder{'s' if len(med_reminders) != 1 else ''}.")
        for r in med_reminders[:2]:
            messages.append(r.message)

    if not messages:
        return {
            "type": "medication",
            "message": "I don't have any medication reminders set up for you.",
            "results": {}
        }

    return {
        "type": "medication",
        "message": " ".join(messages),
        "results": {
            "items": [
                {"item": i.item_name, "room": i.last_seen_room}
                for i in items
            ],
            "reminders": [
                {"message": r.message}
                for r in med_reminders
            ]
        }
    }


async def get_daily_summary(db: AsyncSession, patient_id: UUID) -> dict:
    """
    Get a daily summary including notes and reminders.
    
    Args:
        db: Database session
        patient_id: Patient UUID
        
    Returns:
        Response dict with daily summary
    """
    today = date.today()

    notes_result = await db.execute(
        select(DailyNote).where(
            DailyNote.patient_id == patient_id,
            DailyNote.note_date == today
        )
    )
    notes = notes_result.scalars().all()

    reminder_result = await db.execute(
        select(Reminder).where(
            Reminder.patient_id == patient_id,
            Reminder.active == True
        )
    )
    reminders = reminder_result.scalars().all()

    messages = []

    if notes:
        messages.append("Here are today's notes.")
        for note in notes[:3]:
            messages.append(note.content)

    if reminders:
        messages.append(f"You have {len(reminders)} reminder{'s' if len(reminders) != 1 else ''}.")
        for r in reminders[:3]:
            messages.append(r.message)

    if not messages:
        return {
            "type": "daily_summary",
            "message": "You don't have any notes or reminders for today.",
            "results": {"notes": [], "reminders": []}
        }

    return {
        "type": "daily_summary",
        "message": " ".join(messages),
        "results": {
            "notes": [{"content": n.content} for n in notes],
            "reminders": [{"message": r.message} for r in reminders]
        }
    }


async def process_voice_query(
    db: AsyncSession,
    patient_id: UUID,
    query_text: str
) -> dict:
    """
    Process a voice query and return a speakable response.
    
    This is the main entry point for voice queries. It:
    1. Detects the intent from the query text
    2. Routes to the appropriate handler
    3. Returns a response with a natural language message
    
    Args:
        db: Database session
        patient_id: Patient UUID
        query_text: The transcribed voice query
        
    Returns:
        Response dict with 'type', 'message', and 'results'
    """
    intent_result = detect_voice_intent(query_text)

    if intent_result.intent == VoiceIntent.FIND_ITEM:
        item_name = intent_result.entities.get("item")
        return await get_item_location_response(db, patient_id, item_name)

    if intent_result.intent == VoiceIntent.IDENTIFY_PERSON:
        return await get_last_recognized_person(db, patient_id)

    if intent_result.intent == VoiceIntent.TODAY_REMINDERS:
        return await get_today_reminders(db, patient_id)

    if intent_result.intent == VoiceIntent.MEDICATION:
        return await get_medication_status(db, patient_id)

    if intent_result.intent == VoiceIntent.DAILY_SUMMARY:
        return await get_daily_summary(db, patient_id)

    return {
        "type": "unknown",
        "message": "I'm sorry, I didn't understand that. You can ask me where your things are, who someone is, or what your reminders are.",
        "results": None
    }


def build_person_announcement(
    name: str,
    relationship: Optional[str] = None,
    conversation_prompt: Optional[str] = None
) -> str:
    """
    Build an announcement message for a recognized person.
    
    Args:
        name: Person's name
        relationship: Their relationship to the patient
        conversation_prompt: Optional conversation starter
        
    Returns:
        Announcement message string
    """
    if relationship:
        message = f"This is {name}, your {relationship}."
    else:
        message = f"This is {name}."

    if conversation_prompt:
        message += f" {conversation_prompt}"

    return message


def build_reminder_announcement(message: str) -> str:
    """
    Build a reminder announcement message.
    
    Args:
        message: The reminder message
        
    Returns:
        Formatted reminder announcement
    """
    return f"Reminder: {message}"
