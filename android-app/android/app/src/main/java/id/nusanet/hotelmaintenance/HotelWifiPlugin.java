package id.nusanet.hotelmaintenance;

import android.Manifest;
import android.annotation.TargetApi;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.location.LocationManager;
import android.net.ConnectivityManager;
import android.net.LinkAddress;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.RouteInfo;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import androidx.core.content.ContextCompat;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import org.json.JSONObject;

/** Read-only radio measurements. Never binds traffic, switches Wi-Fi, or fakes results. */
@CapacitorPlugin(name = "HotelWifi", permissions = {
    @Permission(alias = "location", strings = {Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION})
})
public class HotelWifiPlugin extends Plugin {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private PluginCall connectionCall;
    private ConnectionCallback connectionCallback;
    private Runnable connectionTimeout;
    private PluginCall scanCall;
    private BroadcastReceiver scanReceiver;
    private Runnable scanTimeout;
    private long scanStartedUs;

    private WifiManager wifi() { return (WifiManager) getContext().getApplicationContext().getSystemService(Context.WIFI_SERVICE); }
    private ConnectivityManager connectivity() { return (ConnectivityManager) getContext().getSystemService(Context.CONNECTIVITY_SERVICE); }
    private boolean permitted() {
        return ContextCompat.checkSelfPermission(getContext(), Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }
    private boolean locationEnabled() {
        LocationManager manager = (LocationManager) getContext().getSystemService(Context.LOCATION_SERVICE);
        if (manager == null) return false;
        if (Build.VERSION.SDK_INT >= 28) return manager.isLocationEnabled();
        return manager.isProviderEnabled(LocationManager.GPS_PROVIDER) || manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER);
    }
    private static void unavailable(PluginCall call, String reason) {
        call.resolve(new JSObject().put("available", false).put("reason", reason));
    }
    private static String timestamp(long millis) {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        return format.format(new Date(millis));
    }
    private static Object nullable(Object value) { return value == null ? JSONObject.NULL : value; }
    private static String bssid(String value) {
        if (value == null || !value.matches("(?i)([0-9a-f]{2}:){5}[0-9a-f]{2}") ||
            value.equals("02:00:00:00:00:00") || value.equals("00:00:00:00:00:00")) return null;
        return value.toLowerCase(Locale.ROOT);
    }
    private static Integer channel(int frequency) {
        if (frequency == 2484) return 14;
        if (frequency >= 2412 && frequency <= 2472 && (frequency - 2407) % 5 == 0) return (frequency - 2407) / 5;
        if (frequency >= 5000 && frequency <= 5895 && frequency % 5 == 0) return (frequency - 5000) / 5;
        return null;
    }
    private static String band(int frequency) {
        if (frequency >= 2400 && frequency <= 2500) return "2.4 GHz";
        if (frequency >= 5000 && frequency < 5925) return "5 GHz";
        return null;
    }

    @PluginMethod
    public void connection(PluginCall call) {
        if (!permitted()) requestPermissionForAlias("location", call, "locationResult");
        else handler.post(() -> readConnection(call));
    }
    @PluginMethod
    public void scan(PluginCall call) {
        String requestedBand = call.getString("band");
        if (!"2.4 GHz".equals(requestedBand) && !"5 GHz".equals(requestedBand)) {
            call.reject("Band tidak didukung"); return;
        }
        if (!permitted()) requestPermissionForAlias("location", call, "locationResult");
        else handler.post(() -> startScan(call));
    }
    @PermissionCallback
    private void locationResult(PluginCall call) {
        if (!permitted()) { unavailable(call, "Izin lokasi presisi ditolak. Wi-Fi tidak diukur."); return; }
        handler.post(() -> {
            if ("scan".equals(call.getMethodName())) startScan(call);
            else readConnection(call);
        });
    }
    private void readConnection(PluginCall call) {
        if (connectionCall != null) { unavailable(call, "Pembacaan koneksi masih berjalan."); return; }
        connectionCall = call;
        try {
            if (!locationEnabled()) { finishUnavailableConnection(call, "Aktifkan layanan lokasi untuk membaca identitas Wi-Fi."); return; }
            if (wifi() == null || !wifi().isWifiEnabled()) { finishUnavailableConnection(call, "Wi-Fi perangkat tidak aktif."); return; }
            ConnectivityManager manager = connectivity();
            if (manager == null) { finishUnavailableConnection(call, "Layanan jaringan tidak tersedia."); return; }
            connectionCallback = Build.VERSION.SDK_INT >= 31
                ? new ConnectionCallback(call, ConnectivityManager.NetworkCallback.FLAG_INCLUDE_LOCATION_INFO)
                : new ConnectionCallback(call);
            connectionTimeout = () -> finishUnavailableConnection(call, "Koneksi Wi-Fi aktif belum dapat dibaca. Coba kembali.");
            handler.postDelayed(connectionTimeout, 3000);
            manager.registerDefaultNetworkCallback(connectionCallback);
        } catch (SecurityException error) {
            finishUnavailableConnection(call, "Izin membaca koneksi Wi-Fi tidak tersedia.");
        } catch (RuntimeException error) {
            finishUnavailableConnection(call, "Pembacaan Wi-Fi gagal. Coba kembali.");
        }
    }
    private class ConnectionCallback extends ConnectivityManager.NetworkCallback {
        final PluginCall request;
        ConnectionCallback(PluginCall call) { request = call; }
        @TargetApi(31) ConnectionCallback(PluginCall call, int flags) { super(flags); request = call; }
        @Override public void onCapabilitiesChanged(Network network, NetworkCapabilities capabilities) {
            handler.post(() -> finishConnection(request, network, capabilities));
        }
        @Override public void onLost(Network network) {
            handler.post(() -> finishUnavailableConnection(request, "Koneksi berubah saat pengukuran. Baca ulang Wi-Fi."));
        }
    }
    @SuppressWarnings("deprecation")
    private void finishConnection(PluginCall call, Network network, NetworkCapabilities capabilities) {
        if (connectionCall != call) return;
        try {
            if (!network.equals(connectivity().getActiveNetwork()) || !capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
                capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN)) {
                finishUnavailableConnection(call, "Jalur aktif bukan Wi-Fi langsung (seluler/VPN/tidak terhubung)."); return;
            }
            WifiInfo info = null;
            if (Build.VERSION.SDK_INT >= 29 && capabilities.getTransportInfo() instanceof WifiInfo)
                info = (WifiInfo) capabilities.getTransportInfo();
            if (info == null && Build.VERSION.SDK_INT < 31) info = wifi().getConnectionInfo();
            String ssid = info == null ? null : info.getSSID();
            if (WifiManager.UNKNOWN_SSID.equals(ssid)) ssid = null;
            if (ssid != null && ssid.length() >= 2 && ssid.startsWith("\"") && ssid.endsWith("\"")) ssid = ssid.substring(1, ssid.length() - 1);
            int frequency = info == null ? -1 : info.getFrequency();
            int rssi = info == null ? -127 : info.getRssi();
            int speed = info == null ? -1 : info.getLinkSpeed();
            String ip = null, gateway = null;
            LinkProperties properties = connectivity().getLinkProperties(network);
            if (properties != null) {
                for (LinkAddress address : properties.getLinkAddresses()) {
                    InetAddress value = address.getAddress();
                    if (!value.isLoopbackAddress() && !value.isLinkLocalAddress() && (ip == null || value instanceof Inet4Address)) ip = value.getHostAddress();
                }
                for (RouteInfo route : properties.getRoutes()) {
                    InetAddress value = route.getGateway();
                    if (route.isDefaultRoute() && value != null && !value.isAnyLocalAddress() && (gateway == null || value instanceof Inet4Address)) gateway = value.getHostAddress();
                }
            }
            JSObject data = new JSObject().put("source", "android_native").put("transport", "wifi")
                .put("observedAt", timestamp(System.currentTimeMillis())).put("ssid", nullable(ssid))
                .put("bssid", nullable(info == null ? null : bssid(info.getBSSID())))
                .put("frequencyMhz", nullable(frequency > 0 ? frequency : null)).put("channel", nullable(channel(frequency)))
                .put("band", nullable(band(frequency))).put("rssiDbm", nullable(rssi > -127 && rssi <= 0 ? rssi : null))
                .put("linkSpeedMbps", nullable(speed >= 0 ? speed : null)).put("ipAddress", nullable(ip)).put("gateway", nullable(gateway));
            clearConnection();
            call.resolve(new JSObject().put("available", true).put("data", data));
        } catch (SecurityException error) { finishUnavailableConnection(call, "Izin Wi-Fi berubah saat pembacaan."); }
        catch (RuntimeException error) { finishUnavailableConnection(call, "Data koneksi tidak dapat dibaca."); }
    }
    private void finishUnavailableConnection(PluginCall call, String reason) {
        if (connectionCall != call) return;
        clearConnection(); unavailable(call, reason);
    }
    private void clearConnection() {
        if (connectionTimeout != null) handler.removeCallbacks(connectionTimeout);
        if (connectionCallback != null) try { connectivity().unregisterNetworkCallback(connectionCallback); } catch (RuntimeException ignored) { }
        connectionCall = null; connectionCallback = null; connectionTimeout = null;
    }
    private void startScan(PluginCall call) {
        if (scanCall != null) { unavailable(call, "Scan Wi-Fi masih berjalan."); return; }
        try {
            if (!locationEnabled()) { unavailable(call, "Aktifkan layanan lokasi untuk memindai Wi-Fi."); return; }
            if (wifi() == null || !wifi().isWifiEnabled()) { unavailable(call, "Wi-Fi perangkat tidak aktif."); return; }
            scanCall = call;
            scanStartedUs = SystemClock.elapsedRealtimeNanos() / 1000;
            scanReceiver = new BroadcastReceiver() {
                @Override public void onReceive(Context context, Intent intent) {
                    if (!WifiManager.SCAN_RESULTS_AVAILABLE_ACTION.equals(intent.getAction())) return;
                    boolean updated = intent.getBooleanExtra(WifiManager.EXTRA_RESULTS_UPDATED, false);
                    handler.post(() -> finishScan(call, !updated, updated ? null : "Scan baru gagal; menampilkan cache OS."));
                }
            };
            IntentFilter filter = new IntentFilter(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION);
            if (Build.VERSION.SDK_INT >= 33) getContext().registerReceiver(scanReceiver, filter, Context.RECEIVER_EXPORTED);
            else getContext().registerReceiver(scanReceiver, filter);
            scanTimeout = () -> finishScan(call, true, "Scan belum selesai; menampilkan cache OS jika tersedia.");
            handler.postDelayed(scanTimeout, 12000);
            if (!wifi().startScan()) finishScan(call, true, "Scan dibatasi atau gagal; menampilkan cache OS jika tersedia.");
        } catch (SecurityException error) { clearScan(); unavailable(call, "Izin lokasi presisi diperlukan untuk scan Wi-Fi."); }
        catch (RuntimeException error) { clearScan(); unavailable(call, "Scan Wi-Fi gagal. Coba kembali."); }
    }
    @SuppressWarnings("deprecation")
    private void finishScan(PluginCall call, boolean cached, String reason) {
        if (scanCall != call) return;
        try {
            JSArray networks = new JSArray();
            long now = System.currentTimeMillis(), elapsed = SystemClock.elapsedRealtimeNanos() / 1000;
            String requestedBand = call.getString("band");
            for (ScanResult result : wifi().getScanResults()) {
                if (!requestedBand.equals(band(result.frequency)) || bssid(result.BSSID) == null ||
                    result.timestamp <= 0 || result.timestamp > elapsed || result.level < -127 || result.level > 0 || networks.length() >= 256) continue;
                networks.put(new JSObject().put("ssid", result.SSID == null ? "" : result.SSID)
                    .put("bssid", bssid(result.BSSID)).put("frequencyMhz", result.frequency)
                    .put("channel", nullable(channel(result.frequency))).put("rssiDbm", result.level)
                    .put("observedAt", timestamp(now - (elapsed - result.timestamp) / 1000))
                    .put("cached", cached || result.timestamp < scanStartedUs));
            }
            clearScan();
            if (cached && networks.length() == 0) { unavailable(call, reason == null ? "Cache scan belum tersedia." : reason); return; }
            JSObject data = new JSObject().put("source", "android_native").put("band", requestedBand)
                .put("observedAt", timestamp(now)).put("cached", cached).put("reason", nullable(reason)).put("networks", networks);
            call.resolve(new JSObject().put("available", true).put("data", data));
        } catch (SecurityException error) { clearScan(); unavailable(call, "Izin scan berubah; hasil tidak disimpan."); }
        catch (RuntimeException error) { clearScan(); unavailable(call, "Hasil scan tidak dapat dibaca."); }
    }
    private void clearScan() {
        if (scanTimeout != null) handler.removeCallbacks(scanTimeout);
        if (scanReceiver != null) try { getContext().unregisterReceiver(scanReceiver); } catch (RuntimeException ignored) { }
        scanCall = null; scanReceiver = null; scanTimeout = null;
    }
    @Override protected void handleOnDestroy() {
        PluginCall pendingConnection = connectionCall, pendingScan = scanCall;
        clearConnection(); clearScan();
        if (pendingConnection != null) unavailable(pendingConnection, "Pembacaan dibatalkan karena aplikasi ditutup.");
        if (pendingScan != null) unavailable(pendingScan, "Scan dibatalkan karena aplikasi ditutup.");
    }
}
