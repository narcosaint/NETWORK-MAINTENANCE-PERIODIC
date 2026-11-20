import { useId, useState } from "react";
import { Images } from "lucide-react";
import { Message } from "./ui";
export function PhotoPicker({
  label = "Pilih foto dari perangkat",
  disabled = false,
  onFiles,
}: {
  label?: string;
  disabled?: boolean;
  onFiles: (files: File[]) => Promise<void>;
}) {
  const id = useId();
  const [working, setWorking] = useState(false),
    [error, setError] = useState("");
  return (
    <div className="photo-picker">
      <label
        htmlFor={id}
        className={
          "secondary photo-picker-button" +
          (disabled || working ? " is-disabled" : "")
        }
      >
        <Images size={18} />
        {working ? "Menyiapkan foto…" : "Pilih foto"}
        <small>Bisa pilih beberapa foto</small>
      </label>
      <input
        id={id}
        className="file-input"
        aria-label={label}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp"
        disabled={disabled || working}
        onChange={async (e) => {
          const files = Array.from(e.target.files || []);
          e.target.value = "";
          if (!files.length) return;
          setWorking(true);
          setError("");
          try {
            await onFiles(files);
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setWorking(false);
          }
        }}
      />
      {error && <Message error>{error}</Message>}
    </div>
  );
}
