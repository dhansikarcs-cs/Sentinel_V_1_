import json
import os
import streamlit as st

PROFILES_PATH = os.path.join("data", "patient_profiles.json")

DEFAULT_PROFILES = {
    "patients": {
        "alice": {"password": "pass123", "name": "Alice Chen", "trusted_contact": "alice_contact@example.com"},
        "bob": {"password": "pass123", "name": "Bob Martinez", "trusted_contact": "bob_contact@example.com"},
        "charlie": {"password": "pass123", "name": "Charlie Kim", "trusted_contact": "charlie_contact@example.com"},
    },
    "psychologists": {
        "dr.sarah": {"password": "doc123", "name": "Dr. Sarah Blake"},
        "dr.james": {"password": "doc123", "name": "Dr. James Wright"},
    },
}


def _load_profiles():
    if not os.path.exists(PROFILES_PATH):
        os.makedirs(os.path.dirname(PROFILES_PATH), exist_ok=True)
        with open(PROFILES_PATH, "w") as f:
            json.dump(DEFAULT_PROFILES, f, indent=2)
        return DEFAULT_PROFILES
    try:
        with open(PROFILES_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return DEFAULT_PROFILES


def authenticate(username: str, password: str):
    profiles = _load_profiles()
    if username in profiles.get("patients", {}):
        if profiles["patients"][username]["password"] == password:
            return "Patient"
    if username in profiles.get("psychologists", {}):
        if profiles["psychologists"][username]["password"] == password:
            return "Psychologist"
    return None


def get_patient_name(username: str) -> str:
    profiles = _load_profiles()
    return profiles.get("patients", {}).get(username, {}).get("name", username)


def get_psychologist_name(username: str) -> str:
    profiles = _load_profiles()
    return profiles.get("psychologists", {}).get(username, {}).get("name", username)


def get_trusted_contact(patient_username: str) -> str:
    profiles = _load_profiles()
    return profiles.get("patients", {}).get(patient_username, {}).get("trusted_contact", "")


def get_all_patients():
    profiles = _load_profiles()
    return list(profiles.get("patients", {}).keys())
