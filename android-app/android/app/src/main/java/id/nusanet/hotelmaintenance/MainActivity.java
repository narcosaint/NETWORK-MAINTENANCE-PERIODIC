package id.nusanet.hotelmaintenance;

import com.getcapacitor.BridgeActivity;
import android.os.Bundle;

public class MainActivity extends BridgeActivity {
    @Override public void onCreate(Bundle savedInstanceState) {
        registerPlugin(HotelWifiPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
