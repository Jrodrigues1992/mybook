# Prepara o projeto Android gerado pelo Capacitor: recebe PDF/EPUB (Abrir com / Compartilhar) e troca o ícone.
import os, re, shutil
from PIL import Image

ANDROID = 'android'
PKG_DIR = os.path.join(ANDROID, 'app/src/main/java/com/jean/mybook')
os.makedirs(PKG_DIR, exist_ok=True)

MAIN = '''package com.jean.mybook;

import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import com.getcapacitor.BridgeActivity;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(IncomingPlugin.class);
        super.onCreate(savedInstanceState);
        if (savedInstanceState == null) handleIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }

    private void handleIntent(final Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        Uri found = null;
        if (Intent.ACTION_VIEW.equals(action)) {
            found = intent.getData();
        } else if (Intent.ACTION_SEND.equals(action)) {
            found = (Uri) intent.getParcelableExtra(Intent.EXTRA_STREAM);
        }
        if (found == null) return;
        final Uri uri = found;
        intent.setAction(Intent.ACTION_MAIN);
        intent.setData(null);
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    String name = null;
                    Cursor c = getContentResolver().query(uri, null, null, null, null);
                    if (c != null) {
                        try {
                            int i = c.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                            if (i >= 0 && c.moveToFirst()) name = c.getString(i);
                        } finally { c.close(); }
                    }
                    if (name == null || name.length() == 0) name = uri.getLastPathSegment();
                    if (name == null || name.length() == 0) name = "livro";
                    String mime = getContentResolver().getType(uri);
                    String low = name.toLowerCase();
                    if (mime != null && mime.contains("pdf") && !low.endsWith(".pdf")) name = name + ".pdf";
                    else if (mime != null && mime.contains("epub") && !low.endsWith(".epub")) name = name + ".epub";
                    File dir = new File(getCacheDir(), "incoming");
                    dir.mkdirs();
                    String safe = name.replaceAll("[^A-Za-z0-9._-]", "_");
                    File out = new File(dir, System.currentTimeMillis() + "_" + safe);
                    InputStream in = getContentResolver().openInputStream(uri);
                    if (in == null) return;
                    OutputStream os = new FileOutputStream(out);
                    byte[] buf = new byte[65536];
                    int n;
                    while ((n = in.read(buf)) > 0) os.write(buf, 0, n);
                    os.close();
                    in.close();
                    final String path = out.getAbsolutePath();
                    final String finalName = name;
                    final String finalMime = mime == null ? "" : mime;
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() { IncomingPlugin.deliver(path, finalName, finalMime); }
                    });
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }).start();
    }
}
'''

PLUGIN = '''package com.jean.mybook;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "Incoming")
public class IncomingPlugin extends Plugin {
    private static IncomingPlugin instance;
    private static JSObject pending;

    @Override
    public void load() {
        instance = this;
        if (pending != null) {
            notifyListeners("incoming", pending, true);
            pending = null;
        }
    }

    static void deliver(String path, String name, String mime) {
        JSObject o = new JSObject();
        o.put("path", path);
        o.put("name", name);
        o.put("mime", mime);
        if (instance != null) instance.notifyListeners("incoming", o, true);
        else pending = o;
    }
}
'''
open(os.path.join(PKG_DIR, 'MainActivity.java'), 'w', encoding='utf-8').write(MAIN)
open(os.path.join(PKG_DIR, 'IncomingPlugin.java'), 'w', encoding='utf-8').write(PLUGIN)

# Manifesto: filtros para abrir PDF e EPUB
mp = os.path.join(ANDROID, 'app/src/main/AndroidManifest.xml')
m = open(mp, encoding='utf-8').read()
FILTERS = '''
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="content" />
                <data android:scheme="file" />
                <data android:mimeType="application/pdf" />
                <data android:mimeType="application/epub+zip" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.SEND" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="application/pdf" />
                <data android:mimeType="application/epub+zip" />
            </intent-filter>
'''
assert '</intent-filter>' in m, 'manifesto inesperado'
m = m.replace('</intent-filter>', '</intent-filter>' + FILTERS, 1)
open(mp, 'w', encoding='utf-8').write(m)

# Ícone
base = Image.open('icon-512.png').convert('RGBA')
res = os.path.join(ANDROID, 'app/src/main/res')
for d, px in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
    folder = os.path.join(res, 'mipmap-' + d)
    os.makedirs(folder, exist_ok=True)
    img = base.resize((px, px), Image.LANCZOS)
    img.save(os.path.join(folder, 'ic_launcher.png'))
    img.save(os.path.join(folder, 'ic_launcher_round.png'))
shutil.rmtree(os.path.join(res, 'mipmap-anydpi-v26'), ignore_errors=True)
print('Projeto Android preparado.')
