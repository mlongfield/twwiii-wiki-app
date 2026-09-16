"""Publish a built model to Firebase: Cloud Storage snapshot, Firestore entities, site deploy."""


class PublishError(Exception):
    """A publish step failed; the message says what to do next."""
