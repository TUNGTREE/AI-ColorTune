import { create } from 'zustand';
import type { StyleSession, UserProfile, GradingTask, GradingSuggestion, ColorParams } from '../types';
import { saveProfile as saveProfileToStorage } from '../utils/profileStorage';

interface AppState {
  // Style discovery
  session: StyleSession | null;
  profile: UserProfile | null;
  // Steps: 0=style discovery, 1=grading suggestions, 2=finetune, 3=export
  currentStep: number;

  // Grading
  gradingTask: GradingTask | null;
  selectedSuggestion: GradingSuggestion | null;
  // Fine-tuned params carried to export
  finalParams: ColorParams | null;

  setSession: (s: StyleSession | null) => void;
  setProfile: (p: UserProfile | null) => void;
  setStep: (step: number) => void;
  setGradingTask: (t: GradingTask | null) => void;
  setSelectedSuggestion: (s: GradingSuggestion | null) => void;
  setFinalParams: (p: ColorParams | null) => void;
  /** Load a saved profile and jump to grading suggestions step */
  loadSavedProfile: (p: UserProfile) => void;
  goBack: () => void;
  reset: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  session: null,
  profile: null,
  currentStep: 0,
  gradingTask: null,
  selectedSuggestion: null,
  finalParams: null,

  setSession: (session) => set({ session }),
  setProfile: (profile) => {
    if (profile) {
      saveProfileToStorage(profile);
    }
    set({ profile });
  },
  setStep: (currentStep) => set({ currentStep }),
  setGradingTask: (gradingTask) => set({ gradingTask }),
  setSelectedSuggestion: (selectedSuggestion) => set({ selectedSuggestion }),
  setFinalParams: (finalParams) => set({ finalParams }),

  loadSavedProfile: (profile) => {
    set({
      profile,
      session: { id: '', user_id: profile.user_id, status: 'completed', rounds: [] },
      currentStep: 1,
      gradingTask: null,
      selectedSuggestion: null,
      finalParams: null,
    });
  },

  goBack: () => {
    const { currentStep } = get();
    if (currentStep > 0) {
      set({ currentStep: currentStep - 1 });
    }
  },

  reset: () =>
    set({
      session: null,
      profile: null,
      currentStep: 0,
      gradingTask: null,
      selectedSuggestion: null,
      finalParams: null,
    }),
}));
