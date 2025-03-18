"""
Centralised import point for all SQLAlchemy models to resolve circular dependencies.
Imports are ordered to ensure dependent models are loaded after their dependencies.
This ensures all relationships (e.g., `relationship("User")`) are resolvable during
mapper initialisation. Import models from this file instead of individual modules.
"""

from .base import Base                                              # Always import Base first - foundation for all models
from .track import Track                                            # Independent model with no foreign key dependencies
from .locality import Locality                                      # Independent core model
from .locality_track import LocalityTrack                           # Depends on Locality and Track
from .user_session import UserSession                               # Depends on User (but imported after)
from .user_spotify_oauth_account import UserSpotifyOauthAccount     # Depends on User
from .user import User                                              # Depends on multiple models above
from .locality_track_vote import LocalityTrackVote                  # Depends on User and LocalityTrack

__all__ = [
    "Base",
    "Track",
    "Locality",
    "LocalityTrack",
    "UserSession",
    "UserSpotifyOauthAccount",
    "User",
    "LocalityTrackVote"
]