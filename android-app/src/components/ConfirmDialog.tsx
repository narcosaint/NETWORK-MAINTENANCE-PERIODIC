import { useEffect, useRef, useId } from "react";
import { LogOut } from "lucide-react";
export function ConfirmDialog({
  open,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null),
    cancel = useRef<HTMLButtonElement>(null),
    id = useId();
  useEffect(() => {
    if (open) {
      dialog.current?.showModal();
      cancel.current?.focus();
    } else dialog.current?.close();
  }, [open]);
  return (
    <dialog
      ref={dialog}
      className="confirm-dialog"
      aria-labelledby={id}
      onCancel={(e) => {
        e.preventDefault();
        onCancel();
      }}
    >
      <div className="confirm-symbol">
        <LogOut size={26} />
      </div>
      <h2 id={id}>Keluar dari aplikasi?</h2>
      <p>Draf yang belum dikirim tetap tersimpan di perangkat ini.</p>
      <div className="confirm-actions">
        <button ref={cancel} className="secondary" onClick={onCancel}>
          Tetap di sini
        </button>
        <button className="primary" onClick={onConfirm}>
          Ya, keluar
        </button>
      </div>
    </dialog>
  );
}
