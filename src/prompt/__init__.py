from collections.abc import Mapping

from .english import (
    english_base_prompt,
    english_booking_prompt,
    english_rescheduling_prompt,
    english_cancellation_prompt,
    english_status_check_prompt,
    english_emergency_prompt,
    english_general_inquiry_prompt,
)
from .hindi import (
    hindi_prompt,
    hindi_booking_prompt,
    hindi_rescheduling_prompt,
    hindi_cancellation_prompt,
    hindi_status_check_prompt,
    hindi_emergency_prompt,
    hindi_general_inquiry_prompt,
)
from .bengali import (
    bengali_prompt,
    bengali_booking_prompt,
    bengali_rescheduling_prompt,
    bengali_cancellation_prompt,
    bengali_status_check_prompt,
    bengali_emergency_prompt,
    bengali_general_inquiry_prompt,
)


english_prompts = {
    "base": english_base_prompt,
    "Booking": english_booking_prompt,
    "Rescheduling": english_rescheduling_prompt,
    "Cancellation": english_cancellation_prompt,
    "Status_Check": english_status_check_prompt,
    "Emergency": english_emergency_prompt,
    "General_Inquiry": english_general_inquiry_prompt,
}

hindi_prompts = {
    "base": hindi_prompt,
    "Booking": hindi_booking_prompt,    
    "Rescheduling": hindi_rescheduling_prompt,
    "Cancellation": hindi_cancellation_prompt,
    "Status_Check": hindi_status_check_prompt,
    "Emergency": hindi_emergency_prompt,
    "General_Inquiry": hindi_general_inquiry_prompt,
}

bengali_prompts = {
    "base": bengali_prompt,
    "Booking": bengali_booking_prompt,
    "Rescheduling": bengali_rescheduling_prompt,
    "Cancellation": bengali_cancellation_prompt,    
    "Status_Check": bengali_status_check_prompt,
    "Emergency": bengali_emergency_prompt,
    "General_Inquiry": bengali_general_inquiry_prompt,
}


def get_prompt(language: str, intent: str) -> str:
    """
    Retrieve the appropriate prompt based on the specified language and intent.
    """
    language = language.lower()
    intent = intent.capitalize()

    if language == "en" or language == "en-IN":
        prompts = english_prompts
    elif language == "hi" or language == "hi-IN":
        prompts = hindi_prompts
    elif language == "bn" or language == "bn-IN":
        prompts = bengali_prompts
    else:
        raise ValueError(f"Unsupported language: {language}")

    if intent not in prompts:
        raise ValueError(f"Unsupported intent: {intent}")

    return prompts[intent]