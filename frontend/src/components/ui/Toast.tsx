import { useEffect, useState } from 'react';
import { CheckCircle, X } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

interface ToastMessage {
  id: string;
  text: string;
}

let addToastFn: ((text: string) => void) | null = null;

export function showToast(text: string) {
  addToastFn?.(text);
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    addToastFn = (text: string) => {
      const id = crypto.randomUUID();
      setToasts((prev) => [...prev, { id, text }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 2500);
    };
    return () => {
      addToastFn = null;
    };
  }, []);

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            className="flex items-center gap-2 px-4 py-3 glass rounded-xl text-sm text-white font-medium"
          >
            <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            {toast.text}
            <button
              onClick={() =>
                setToasts((prev) => prev.filter((t) => t.id !== toast.id))
              }
              className="ml-2 text-gray-400 hover:text-white"
            >
              <X className="w-3 h-3" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
