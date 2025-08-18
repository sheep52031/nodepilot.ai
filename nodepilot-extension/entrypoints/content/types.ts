export interface AnnotationData {
  id?: number;
  url: string;
  selected_text: string;
  confusion_note: string;
  teaching_content?: string;
  status: 'unknown' | 'learning' | 'understood';
  created_at?: string;
}

export interface TeachingRequest {
  url: string;
  selected_text: string;
  confusion_note: string;
  audio_file?: Blob;
}

export interface APIResponse {
  id: number;
  url: string;
  selected_text: string;
  confusion_note: string;
  teaching_content: string;
  status: string;
  created_at: string;
}

export interface NodePilotState {
  currentAnnotation: AnnotationData | null;
  isLoading: boolean;
  error: string | null;
  showUI: boolean;
}

export type NodePilotAction = 
  | { type: 'SET_ANNOTATION'; payload: AnnotationData }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SHOW_UI'; payload: boolean }
  | { type: 'CLEAR_STATE' };