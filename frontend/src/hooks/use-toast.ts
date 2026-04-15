import { useState } from 'react';

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: 'default' | 'destructive';
}

const toasts: Toast[] = [];
let toastListeners: ((toasts: Toast[]) => void)[] = [];

export function useToast() {
  const [, setToasts] = useState<Toast[]>([]);

  const toast = ({ title, description, variant = 'default' }: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newToast: Toast = { id, title, description, variant };
    toasts.push(newToast);

    toastListeners.forEach((listener) => listener([...toasts]));

    // Auto-dismiss after 3 seconds
    setTimeout(() => {
      const index = toasts.findIndex((t) => t.id === id);
      if (index !== -1) {
        toasts.splice(index, 1);
        toastListeners.forEach((listener) => listener([...toasts]));
      }
    }, 3000);
  };

  const dismiss = (id: string) => {
    const index = toasts.findIndex((t) => t.id === id);
    if (index !== -1) {
      toasts.splice(index, 1);
      toastListeners.forEach((listener) => listener([...toasts]));
    }
  };

  return { toast, dismiss, toasts };
}
