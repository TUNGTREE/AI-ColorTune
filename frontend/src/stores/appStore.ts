import { create } from 'zustand';
import type { StyleSession, UserProfile, GradingTask, GradingSuggestion, ColorParams } from '../types';

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
  setProfile: (profile) => set({ profile }),
  setStep: (currentStep) => set({ currentStep }),
  setGradingTask: (gradingTask) => set({ gradingTask }),
  setSelectedSuggestion: (selectedSuggestion) => set({ selectedSuggestion }),
  setFinalParams: (finalParams) => set({ finalParams }),

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
