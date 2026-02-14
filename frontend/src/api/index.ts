import axios from 'axios';
import type {
  StyleSession,
  StyleOption,
  StyleRound,
  UserProfile,
  GradingTask,
  GradingSuggestion,
  SampleScene,
} from '../types';

const api = axios.create({ baseURL: 'http://localhost:8000' });

export const styleApi = {
  createSession: () =>
    api.post<StyleSession>('/api/style/sessions', {}).then((r) => r.data),

  getSession: (id: string) =>
    api.get<StyleSession>(`/api/style/sessions/${id}`).then((r) => r.data),

  createRound: (sessionId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api
      .post<StyleRound>(`/api/style/sessions/${sessionId}/rounds`, form)
      .then((r) => r.data);
  },

  getSamples: () =>
    api.get<SampleScene[]>('/api/style/samples').then((r) => r.data),

  createRoundFromSample: (sessionId: string, sampleId: string) =>
    api
      .post<StyleRound>(`/api/style/sessions/${sessionId}/rounds/sample`, {
        sample_id: sampleId,
      })
      .then((r) => r.data),

  getRoundOptions: (roundId: string) =>
    api.get<StyleOption[]>(`/api/style/rounds/${roundId}/options`).then((r) => r.data),

  selectOption: (roundId: string, optionId: string) =>
    api
      .post<StyleOption>(`/api/style/rounds/${roundId}/select`, { option_id: optionId })
      .then((r) => r.data),

  regenerateOptions: (roundId: string) =>
    api
      .post<StyleRound>(`/api/style/rounds/${roundId}/regenerate`)
      .then((r) => r.data),

  analyzeSession: (sessionId: string) =>
    api.post<UserProfile>(`/api/style/sessions/${sessionId}/analyze`).then((r) => r.data),

  getProfile: (profileId: string) =>
    api.get<UserProfile>(`/api/style/profiles/${profileId}`).then((r) => r.data),
};

export const gradingApi = {
  createTask: (userId: string, file: File, profileId?: string) => {
    const form = new FormData();
    form.append('file', file);
    form.append('user_id', userId);
    if (profileId) form.append('profile_id', profileId);
    return api.post<GradingTask>('/api/grading/tasks', form).then((r) => r.data);
  },

  getTask: (taskId: string) =>
    api.get<GradingTask>(`/api/grading/tasks/${taskId}`).then((r) => r.data),

  generateSuggestions: (taskId: string, num = 3) =>
    api
      .post<GradingSuggestion[]>(`/api/grading/tasks/${taskId}/suggest`, {
        num_suggestions: num,
      })
      .then((r) => r.data),

  getSuggestions: (taskId: string) =>
    api
      .get<GradingSuggestion[]>(`/api/grading/tasks/${taskId}/suggestions`)
      .then((r) => r.data),

  regenerateSuggestions: (taskId: string, num = 3) =>
    api
      .post<GradingSuggestion[]>(`/api/grading/tasks/${taskId}/regenerate-suggestions`, {
        num_suggestions: num,
      })
      .then((r) => r.data),

  selectSuggestion: (suggestionId: string) =>
    api
      .post<GradingSuggestion>(`/api/grading/suggestions/${suggestionId}/select`)
      .then((r) => r.data),

  preview: (taskId: string, parameters: Record<string, unknown>) =>
    api
      .post<{ preview_url: string }>(`/api/grading/tasks/${taskId}/preview`, {
        parameters,
      })
      .then((r) => r.data),

  exportImage: (
    taskId: string,
    parameters: Record<string, unknown>,
    format = 'jpeg',
    quality = 95,
  ) =>
    api
      .post<{
        id: string;
        task_id: string;
        output_url: string | null;
        export_format: string;
        quality: number;
      }>(`/api/grading/tasks/${taskId}/export`, {
        parameters,
        format,
        quality,
      })
      .then((r) => r.data),

  downloadExport: (exportId: string) =>
    `http://localhost:8000/api/grading/exports/${exportId}/download`,
};

export const aiApi = {
  getProviders: () =>
    api
      .get<{
        providers: string[];
        provider_labels: Record<string, string>;
        default_models: Record<string, string>;
        current: string;
        model: string;
        base_url: string;
        api_key_masked: string;
        api_key_set: boolean;
      }>('/api/ai/providers')
      .then((r) => r.data),

  setProvider: (config: {
    provider: string;
    api_key?: string;
    model?: string;
    base_url?: string;
  }) => api.put<{ status: string; provider: string }>('/api/ai/provider', config).then((r) => r.data),
};

export const uploadApi = {
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.post<{ id: string; filename: string }>('/api/upload', form).then((r) => r.data);
  },
};

export default api;
