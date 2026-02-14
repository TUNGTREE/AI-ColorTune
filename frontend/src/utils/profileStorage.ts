import type { UserProfile } from '../types';

const STORAGE_KEY = 'colortune_saved_profiles';

export interface SavedProfile {
  /** The profile data from the backend */
  profile: UserProfile;
  /** User-given name or auto-generated label */
  name: string;
  /** When the profile was saved */
  savedAt: string;
}

export function getSavedProfiles(): SavedProfile[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as SavedProfile[];
  } catch {
    return [];
  }
}

export function saveProfile(profile: UserProfile, name?: string): SavedProfile {
  const profiles = getSavedProfiles();
  // Auto-generate name if not provided
  const autoName = name || `Profile ${profiles.length + 1}`;
  const saved: SavedProfile = {
    profile,
    name: autoName,
    savedAt: new Date().toISOString(),
  };
  // Avoid duplicates by profile.id
  const filtered = profiles.filter((p) => p.profile.id !== profile.id);
  filtered.unshift(saved);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  return saved;
}

export function deleteProfile(profileId: string): void {
  const profiles = getSavedProfiles();
  const filtered = profiles.filter((p) => p.profile.id !== profileId);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
}

export function renameProfile(profileId: string, newName: string): void {
  const profiles = getSavedProfiles();
  const target = profiles.find((p) => p.profile.id === profileId);
  if (target) {
    target.name = newName;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profiles));
  }
}
