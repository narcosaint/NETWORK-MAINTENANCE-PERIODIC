package id.nusanet.hotelmaintenance;

import android.content.Intent;
import android.net.Uri;
import android.util.Base64;
import androidx.core.content.FileProvider;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.File;
import java.io.FileOutputStream;

@CapacitorPlugin(name = "HotelDocuments")
public class HotelDocumentsPlugin extends Plugin {
    @PluginMethod
    public void sharePdf(PluginCall call) {
        String name = call.getString("filename");
        String encoded = call.getString("data_base64");
        if (name == null || name.length() > 200 || !name.matches("Nusa(?: Maintenance|-Maintenance)-[A-Za-z0-9][A-Za-z0-9 _-]*\\.pdf") || encoded == null || encoded.length() > 100000000) {
            call.reject("Berkas PDF tidak valid"); return;
        }
        try {
            byte[] bytes = Base64.decode(encoded, Base64.DEFAULT);
            if (bytes.length < 5 || bytes[0] != '%' || bytes[1] != 'P' || bytes[2] != 'D' || bytes[3] != 'F') {
                call.reject("Berkas bukan PDF"); return;
            }
            File directory = new File(getContext().getCacheDir(), "maintenance-pdf");
            if (!directory.exists() && !directory.mkdirs()) throw new java.io.IOException("Cannot create PDF cache");
            File target = new File(directory, name);
            try (FileOutputStream out = new FileOutputStream(target)) { out.write(bytes); }
            Uri uri = FileProvider.getUriForFile(getContext(), getContext().getPackageName() + ".fileprovider", target);
            Intent intent = new Intent(Intent.ACTION_SEND);
            intent.setType("application/pdf"); intent.putExtra(Intent.EXTRA_STREAM, uri);
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            getActivity().runOnUiThread(() -> {
                try { getActivity().startActivity(Intent.createChooser(intent, "Simpan / bagikan laporan PDF")); call.resolve(); }
                catch (Exception ex) { call.reject("Aplikasi pembuka PDF tidak tersedia", ex); }
            });
        } catch (Exception ex) { call.reject("PDF gagal disiapkan", ex); }
    }
}
