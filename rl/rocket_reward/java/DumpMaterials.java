import info.openrocket.core.database.Databases;
import info.openrocket.core.material.Material;
import info.openrocket.core.preset.ComponentPreset;
import info.openrocket.core.preset.xml.OpenRocketComponentLoader;
import info.openrocket.core.startup.OpenRocketCore;

import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import java.util.prefs.AbstractPreferences;
import java.util.prefs.Preferences;
import java.util.prefs.PreferencesFactory;

/**
 * Prints OpenRocket's own material list as one JSON object on standard output.
 *
 * Used only to rebuild rocket_reward/data/material_table.json (see
 * rocket_reward/tools/build_material_table.py); the reward never runs it.
 *
 * Usage: java -cp "OpenRocket.jar;classes" DumpMaterials OpenRocket.jar
 *
 * Output:
 *   {"builtin":  [{"type", "name", "density"}, ...],
 *    "presets":  [{"file", "type", "name", "density", "parts"}, ...],
 *    "declared": [{"file", "type", "name", "density", "units"}, ...],
 *    "preset_files": [{"file", "presets"}, ...]}
 *
 * "builtin" is OpenRocket's material database (Databases.BULK_MATERIAL,
 * SURFACE_MATERIAL and LINE_MATERIAL) as it stands right after start-up.
 * "presets" are the materials of the component preset files (.orc) shipped
 * inside the jar, read with OpenRocket's own preset reader: each preset's
 * material and, for parachutes, its line material, with the number of parts
 * that use it. "declared" are the materials each preset file lists in its
 * Materials section, used by a part or not. Densities are in SI units
 * (kg/m3 bulk, kg/m2 surface, kg/m line). Nothing is read from or written to
 * the user's OpenRocket settings.
 */
public class DumpMaterials {

    /** Separates the fields of a map key; it never occurs in a material name. */
    static final String SEP = "\t|\t";

    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("usage: DumpMaterials <OpenRocket jar>");
            System.exit(2);
        }
        PrintStream reply = new PrintStream(new FileOutputStream(FileDescriptor.out), false, "UTF-8");
        // OpenRocket's own messages go to standard error, so standard output holds only the JSON.
        System.setOut(System.err);
        System.setProperty("java.awt.headless", "true");
        System.setProperty("java.util.prefs.PreferencesFactory", MemoryPrefsFactory.class.getName());
        Locale.setDefault(Locale.US);
        MemoryPrefsFactory.USER.node("OpenRocket-core").put("UserThrustCurves", "");
        OpenRocketCore.initialize(new info.openrocket.core.plugin.PluginModule(), new com.google.inject.AbstractModule() {
            @Override
            protected void configure() {
                bind(info.openrocket.core.database.ComponentPresetDao.class)
                        .to(info.openrocket.core.database.ComponentPresetDatabase.class);
            }
        });

        StringBuilder out = new StringBuilder();
        out.append("{\"builtin\": [");
        boolean first = true;
        Material.Type[] kinds = {Material.Type.BULK, Material.Type.SURFACE, Material.Type.LINE};
        for (Material.Type kind : kinds) {
            List<Material> list = new ArrayList<>(Databases.getDatabase(kind));
            for (Material m : list) {
                if (m.isUserDefined() || m.isDocumentMaterial()) continue;
                out.append(first ? "\n  " : ",\n  ");
                first = false;
                out.append("{\"type\": ").append(str(typeName(kind)))
                   .append(", \"name\": ").append(str(m.getName()))
                   .append(", \"density\": ").append(num(m.getDensity())).append("}");
            }
        }

        // file -> (type, name, density) key -> number of parts, in a stable order
        Map<String, Map<String, Integer>> used = new TreeMap<>();
        Map<String, List<String[]>> declared = new TreeMap<>();
        Map<String, Integer> presetCounts = new TreeMap<>();
        try (JarFile jar = new JarFile(args[0])) {
            List<String> names = new ArrayList<>();
            for (Enumeration<JarEntry> e = jar.entries(); e.hasMoreElements(); ) {
                String n = e.nextElement().getName();
                if (n.startsWith("datafiles/components/") && n.toLowerCase(Locale.ROOT).endsWith(".orc")) {
                    names.add(n);
                }
            }
            Collections.sort(names);
            for (String n : names) {
                Collection<ComponentPreset> presets;
                try (InputStream in = jar.getInputStream(jar.getJarEntry(n))) {
                    presets = new OpenRocketComponentLoader().load(in, n);
                }
                presetCounts.put(n, presets.size());
                Map<String, Integer> perFile = used.computeIfAbsent(n, k -> new TreeMap<>());
                for (ComponentPreset p : presets) {
                    note(perFile, p.has(ComponentPreset.MATERIAL) ? p.get(ComponentPreset.MATERIAL) : null);
                    note(perFile, p.has(ComponentPreset.LINE_MATERIAL) ? p.get(ComponentPreset.LINE_MATERIAL) : null);
                }
                try (InputStream in = jar.getInputStream(jar.getJarEntry(n))) {
                    declared.put(n, declaredMaterials(in));
                }
            }
        }

        out.append("\n],\n\"presets\": [");
        first = true;
        for (Map.Entry<String, Map<String, Integer>> f : used.entrySet()) {
            for (Map.Entry<String, Integer> m : f.getValue().entrySet()) {
                String[] parts = m.getKey().split(java.util.regex.Pattern.quote(SEP), -1);
                out.append(first ? "\n  " : ",\n  ");
                first = false;
                out.append("{\"file\": ").append(str(f.getKey()))
                   .append(", \"type\": ").append(str(parts[0]))
                   .append(", \"name\": ").append(str(parts[1]))
                   .append(", \"density\": ").append(parts[2])
                   .append(", \"parts\": ").append(m.getValue()).append("}");
            }
        }
        out.append("\n],\n\"declared\": [");
        first = true;
        for (Map.Entry<String, List<String[]>> f : declared.entrySet()) {
            for (String[] parts : f.getValue()) {
                out.append(first ? "\n  " : ",\n  ");
                first = false;
                out.append("{\"file\": ").append(str(f.getKey()))
                   .append(", \"type\": ").append(str(parts[0]))
                   .append(", \"name\": ").append(str(parts[1]))
                   .append(", \"density\": ").append(parts[2])
                   .append(", \"units\": ").append(str(parts[3])).append("}");
            }
        }
        out.append("\n],\n\"preset_files\": [");
        first = true;
        for (Map.Entry<String, Integer> f : presetCounts.entrySet()) {
            out.append(first ? "\n  " : ",\n  ");
            first = false;
            out.append("{\"file\": ").append(str(f.getKey())).append(", \"presets\": ").append(f.getValue()).append("}");
        }
        out.append("\n]}\n");
        reply.print(out);
        reply.flush();
        System.exit(0);
    }

    /**
     * The materials a preset file lists in its Materials section, read the way
     * OpenRocket reads them: the density number is taken as SI whatever the
     * UnitsOfMeasure attribute says (OpenRocket's own reader ignores it too).
     * The attribute is passed on so the build tool can report odd units.
     */
    static List<String[]> declaredMaterials(InputStream in) throws Exception {
        javax.xml.parsers.DocumentBuilderFactory f = javax.xml.parsers.DocumentBuilderFactory.newInstance();
        f.setExpandEntityReferences(false);
        f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        org.w3c.dom.Document doc = f.newDocumentBuilder().parse(in);
        List<String[]> result = new ArrayList<>();
        org.w3c.dom.NodeList groups = doc.getElementsByTagName("Materials");
        for (int g = 0; g < groups.getLength(); g++) {
            org.w3c.dom.NodeList kids = groups.item(g).getChildNodes();
            for (int i = 0; i < kids.getLength(); i++) {
                if (!(kids.item(i) instanceof org.w3c.dom.Element)) continue;
                org.w3c.dom.Element m = (org.w3c.dom.Element) kids.item(i);
                if (!"Material".equals(m.getTagName())) continue;
                String name = text(m, "Name");
                String type = text(m, "Type");
                String density = text(m, "Density");
                if (name == null || type == null || density == null) continue;
                double d;
                try {
                    d = Double.parseDouble(density.trim());
                } catch (NumberFormatException e) {
                    continue;
                }
                result.add(new String[] {type.trim().toLowerCase(Locale.ROOT), name, num(d),
                        m.getAttribute("UnitsOfMeasure")});
            }
        }
        return result;
    }

    static String text(org.w3c.dom.Element parent, String tag) {
        org.w3c.dom.NodeList l = parent.getElementsByTagName(tag);
        return l.getLength() == 0 ? null : l.item(0).getTextContent();
    }

    static void note(Map<String, Integer> perFile, Material m) {
        if (m == null) return;
        String key = typeName(m.getType()) + SEP + m.getName() + SEP + num(m.getDensity());
        perFile.merge(key, 1, Integer::sum);
    }

    static String typeName(Material.Type t) {
        return t.name().toLowerCase(Locale.ROOT);
    }

    static String num(double d) {
        if (Double.isNaN(d) || Double.isInfinite(d)) return "null";
        return Double.toString(d);
    }

    static String str(String s) {
        if (s == null) return "null";
        StringBuilder b = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '"' || c == '\\') b.append('\\').append(c);
            else if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
            else b.append(c);
        }
        return b.append('"').toString();
    }

    // ------------------------------------------------------------------ in-memory preferences

    /** java.util.prefs replacement: nothing is read from or written to the machine. */
    public static final class MemoryPrefsFactory implements PreferencesFactory {
        static final MemoryPrefs USER = new MemoryPrefs(null, "");
        static final MemoryPrefs SYSTEM = new MemoryPrefs(null, "");
        public MemoryPrefsFactory() { }
        @Override public Preferences userRoot() { return USER; }
        @Override public Preferences systemRoot() { return SYSTEM; }
    }

    static final class MemoryPrefs extends AbstractPreferences {
        private final Map<String, String> values = new HashMap<>();
        private final Map<String, MemoryPrefs> children = new HashMap<>();
        MemoryPrefs(MemoryPrefs parent, String name) { super(parent, name); }
        @Override protected void putSpi(String key, String value) { values.put(key, value); }
        @Override protected String getSpi(String key) { return values.get(key); }
        @Override protected void removeSpi(String key) { values.remove(key); }
        @Override protected void removeNodeSpi() { }
        @Override protected String[] keysSpi() { return values.keySet().toArray(new String[0]); }
        @Override protected String[] childrenNamesSpi() { return children.keySet().toArray(new String[0]); }
        @Override protected AbstractPreferences childSpi(String name) {
            return children.computeIfAbsent(name, n -> new MemoryPrefs(this, n));
        }
        @Override protected void syncSpi() { }
        @Override protected void flushSpi() { }
    }
}
