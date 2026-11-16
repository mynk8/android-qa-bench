package aqb.probe;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.os.Bundle;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

/**
 * Data access for benchmark checks on devices without root (Limrun, phones).
 *
 * Runs inside the target app's process through `am instrument`, so it can read and
 * write that app's private files and databases. Signed with the same debug key as
 * the app builds. Input: -e op <sql|exec|cat|write|find> -e arg <base64 JSON>.
 * Output: instrumentation result key "out" = base64 JSON {"ok":..., ...}.
 */
public class Probe extends Instrumentation {
    private Bundle args;

    @Override
    public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        args = arguments;
        start();
    }

    @Override
    public void onStart() {
        String out;
        try {
            out = run();
        } catch (Throwable t) {
            out = "{\"ok\":false,\"error\":" + JSONObject.quote(t.getClass().getSimpleName() + ": " + t.getMessage()) + "}";
        }
        Bundle res = new Bundle();
        res.putString("out", Base64.encodeToString(out.getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP));
        finish(Activity.RESULT_OK, res);
    }

    private String run() throws Exception {
        Context ctx = getTargetContext();
        String op = args.getString("op", "");
        String argB64 = args.getString("arg", "e30=");
        JSONObject in = new JSONObject(new String(Base64.decode(argB64, Base64.DEFAULT), StandardCharsets.UTF_8));
        JSONObject out = new JSONObject();
        switch (op) {
            case "find": {
                File f = resolve(ctx, in.getString("name"));
                out.put("ok", f != null);
                if (f != null) out.put("path", f.getAbsolutePath());
                return out.toString();
            }
            case "sql": {
                File f = resolve(ctx, in.getString("db"));
                if (f == null) throw new java.io.FileNotFoundException(in.getString("db"));
                SQLiteDatabase db = SQLiteDatabase.openDatabase(f.getPath(), null, SQLiteDatabase.OPEN_READWRITE);
                JSONArray rows = new JSONArray();
                try (Cursor c = db.rawQuery(in.getString("query"), null)) {
                    String[] cols = c.getColumnNames();
                    while (c.moveToNext()) {
                        JSONObject row = new JSONObject();
                        for (int i = 0; i < cols.length; i++) {
                            switch (c.getType(i)) {
                                case Cursor.FIELD_TYPE_NULL: row.put(cols[i], JSONObject.NULL); break;
                                case Cursor.FIELD_TYPE_INTEGER: row.put(cols[i], c.getLong(i)); break;
                                case Cursor.FIELD_TYPE_FLOAT: row.put(cols[i], c.getDouble(i)); break;
                                case Cursor.FIELD_TYPE_BLOB:
                                    row.put(cols[i], Base64.encodeToString(c.getBlob(i), Base64.NO_WRAP)); break;
                                default: row.put(cols[i], c.getString(i));
                            }
                        }
                        rows.put(row);
                    }
                } finally {
                    db.close();
                }
                out.put("ok", true);
                out.put("rows", rows);
                return out.toString();
            }
            case "exec": {
                File f = resolve(ctx, in.getString("db"));
                if (f == null) throw new java.io.FileNotFoundException(in.getString("db"));
                SQLiteDatabase db = SQLiteDatabase.openDatabase(f.getPath(), null, SQLiteDatabase.OPEN_READWRITE);
                try {
                    db.execSQL("PRAGMA foreign_keys=OFF");
                    JSONArray st = in.getJSONArray("statements");
                    db.beginTransaction();
                    try {
                        for (int i = 0; i < st.length(); i++) db.execSQL(st.getString(i));
                        db.setTransactionSuccessful();
                    } finally {
                        db.endTransaction();
                    }
                } finally {
                    db.close();
                }
                out.put("ok", true);
                return out.toString();
            }
            case "cat": {
                File f = new File(ctx.getDataDir(), in.getString("path"));
                out.put("ok", f.isFile());
                if (f.isFile()) out.put("b64", Base64.encodeToString(read(f), Base64.NO_WRAP));
                return out.toString();
            }
            case "write": {
                File f = new File(ctx.getDataDir(), in.getString("path"));
                File parent = f.getParentFile();
                if (parent != null) parent.mkdirs();
                try (FileOutputStream os = new FileOutputStream(f)) {
                    os.write(Base64.decode(in.getString("b64"), Base64.DEFAULT));
                }
                out.put("ok", true);
                return out.toString();
            }
            default:
                throw new IllegalArgumentException("unknown op " + op);
        }
    }

    /** A database or file by name: the app's database dir first, then anywhere in its data dir. */
    private static File resolve(Context ctx, String name) {
        if (name.startsWith("/")) {
            File f = new File(name);
            return f.isFile() ? f : null;
        }
        File f = ctx.getDatabasePath(name);
        if (f.isFile()) return f;
        return search(ctx.getDataDir(), name, 6);
    }

    private static File search(File dir, String name, int depth) {
        if (dir == null || depth < 0) return null;
        File[] kids = dir.listFiles();
        if (kids == null) return null;
        for (File k : kids) if (k.isFile() && k.getName().equals(name)) return k;
        for (File k : kids) if (k.isDirectory()) {
            File r = search(k, name, depth - 1);
            if (r != null) return r;
        }
        return null;
    }

    private static byte[] read(File f) throws Exception {
        try (InputStream is = new FileInputStream(f); ByteArrayOutputStream bo = new ByteArrayOutputStream()) {
            byte[] buf = new byte[65536];
            int n;
            while ((n = is.read(buf)) > 0) bo.write(buf, 0, n);
            return bo.toByteArray();
        }
    }
}
