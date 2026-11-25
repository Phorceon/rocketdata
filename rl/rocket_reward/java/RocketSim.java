import info.openrocket.core.aerodynamics.BarrowmanCalculator;
import info.openrocket.core.aerodynamics.FlightConditions;
import info.openrocket.core.document.OpenRocketDocument;
import info.openrocket.core.document.Simulation;
import info.openrocket.core.file.GeneralRocketLoader;
import info.openrocket.core.logging.Message;
import info.openrocket.core.logging.WarningSet;
import info.openrocket.core.masscalc.MassCalculator;
import info.openrocket.core.masscalc.RigidBody;
import info.openrocket.core.models.wind.MultiLevelPinkNoiseWindModel;
import info.openrocket.core.models.wind.PinkNoiseWindModel;
import info.openrocket.core.models.wind.WindModelType;
import info.openrocket.core.motor.Motor;
import info.openrocket.core.motor.MotorConfiguration;
import info.openrocket.core.motor.ThrustCurveMotor;
import info.openrocket.core.rocketcomponent.AxialStage;
import info.openrocket.core.rocketcomponent.BodyTube;
import info.openrocket.core.rocketcomponent.DeploymentConfiguration;
import info.openrocket.core.rocketcomponent.FinSet;
import info.openrocket.core.rocketcomponent.FlightConfiguration;
import info.openrocket.core.rocketcomponent.FlightConfigurationId;
import info.openrocket.core.rocketcomponent.MassObject;
import info.openrocket.core.rocketcomponent.MotorMount;
import info.openrocket.core.rocketcomponent.Parachute;
import info.openrocket.core.rocketcomponent.RailButton;
import info.openrocket.core.rocketcomponent.RecoveryDevice;
import info.openrocket.core.rocketcomponent.RingComponent;
import info.openrocket.core.rocketcomponent.Rocket;
import info.openrocket.core.rocketcomponent.RocketComponent;
import info.openrocket.core.rocketcomponent.Streamer;
import info.openrocket.core.rocketcomponent.SymmetricComponent;
import info.openrocket.core.rocketcomponent.TrapezoidFinSet;
import info.openrocket.core.rocketcomponent.Tube;
import info.openrocket.core.simulation.FlightData;
import info.openrocket.core.simulation.FlightDataBranch;
import info.openrocket.core.simulation.FlightDataType;
import info.openrocket.core.simulation.FlightEvent;
import info.openrocket.core.simulation.SimulationOptions;
import info.openrocket.core.simulation.SimulationStatus;
import info.openrocket.core.simulation.exception.SimulationException;
import info.openrocket.core.simulation.listeners.AbstractSimulationListener;
import info.openrocket.core.startup.Application;
import info.openrocket.core.startup.OpenRocketCore;
import info.openrocket.core.util.Coordinate;
import info.openrocket.core.util.GeodeticComputationStrategy;

import org.xml.sax.Attributes;
import org.xml.sax.InputSource;
import org.xml.sax.helpers.DefaultHandler;

import javax.xml.parsers.SAXParser;
import javax.xml.parsers.SAXParserFactory;
import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileDescriptor;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.PrintStream;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.IdentityHashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.zip.GZIPInputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.prefs.AbstractPreferences;
import java.util.prefs.Preferences;
import java.util.prefs.PreferencesFactory;

/**
 * Small helper that drives OpenRocket 24.12 for the rocket_reward package.
 *
 * It reads one JSON request per line on standard input and writes exactly one
 * JSON reply line per request on standard output. The protocol is described in
 * PROTOCOL.md next to this file. Everything else (OpenRocket's own log text,
 * Java warnings, our own notes) goes to standard error.
 *
 * Design rules kept here:
 * - No user preferences are read or written: java.util.prefs is replaced by an
 *   in-memory store before OpenRocket starts, so several helpers can run at the
 *   same time and nothing on the machine changes the numbers.
 * - Every launch condition is set by this helper; simulations stored in the
 *   file are ignored.
 * - Runs are repeatable: part ids come from a seeded random source, the wind
 *   model is rebuilt from each flight's seed, and the file is loaded again
 *   before every flight.
 * - Faults of the design become "load" or "build" errors or a failed flight.
 *   Only a bug in this helper is "internal".
 */
public class RocketSim {

    static final int HELPER_VERSION = 4;
    static final String OPENROCKET_VERSION = "24.12";
    /** Start of the load warning OpenRocket gives when it skips a value it cannot read (Warning.FILE_INVALID_PARAMETER). */
    static final String INVALID_PARAMETER_WARNING = "Invalid parameter encountered";
    /** Seed for the random ids OpenRocket gives parts while loading a file. */
    static final long PART_ID_SEED = 42L;
    /** Mach number at which the static centre of pressure is reported (OpenRocket's own default). */
    static final double STATIC_CP_MACH = 0.3;
    /** Wind direction used when the request gives none: OpenRocket's built-in default (wind from the east, 90 degrees). */
    static final double DEFAULT_WIND_DIRECTION_DEG = 90.0;

    /** The real standard output. Only reply lines are written here. */
    static PrintStream reply;
    static String bootError = null;

    // ------------------------------------------------------------------ start-up

    public static void main(String[] args) throws Exception {
        reply = new PrintStream(new FileOutputStream(FileDescriptor.out), false, "UTF-8");
        // Anything that writes to System.out from now on (OpenRocket, logging) lands on standard error.
        System.setOut(System.err);
        System.setProperty("java.awt.headless", "true");
        System.setProperty("java.util.prefs.PreferencesFactory", MemoryPrefsFactory.class.getName());
        Locale.setDefault(Locale.US);
        try {
            boot();
        } catch (Throwable t) {
            bootError = describe(t);
            System.err.println("RocketSim: OpenRocket did not start: " + bootError);
            t.printStackTrace(System.err);
        }
        // Standard input is read on its own thread. When it closes (the parent process ended,
        // even by a hard kill in the middle of a long flight) the helper exits at once instead
        // of finishing the request nobody is waiting for.
        BlockingQueue<String> requests = new LinkedBlockingQueue<>();
        Thread stdinReader = new Thread(() -> {
            try {
                BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
                String l;
                while ((l = in.readLine()) != null) requests.add(l);
            } catch (Throwable t) {
                System.err.println("RocketSim: standard input failed: " + t);
            }
            System.err.println("RocketSim: standard input closed; exiting");
            reply.flush();
            System.exit(0);
        }, "rocketsim-stdin");
        stdinReader.setDaemon(true);
        stdinReader.start();
        while (true) {
            String line = requests.take();
            if (line.trim().isEmpty()) continue;
            Object id = null;
            String out;
            try {
                Object parsed = Json.parse(line);
                if (!(parsed instanceof Map)) throw new BadRequest("the request is not a JSON object");
                @SuppressWarnings("unchecked")
                Map<String, Object> req = (Map<String, Object>) parsed;
                id = req.get("id");
                Object op = req.get("op");
                if ("quit".equals(op)) break;
                if (bootError != null) {
                    out = Json.write(internal(id, "OpenRocket did not start: " + bootError));
                } else if ("ping".equals(op)) {
                    out = Json.write(ping(id));
                } else if ("run".equals(op)) {
                    out = Json.write(run(id, req));
                } else if ("motors".equals(op)) {
                    out = Json.write(motors(id));
                } else {
                    throw new BadRequest("unknown op " + Json.write(op));
                }
            } catch (BadRequest e) {
                // The caller sent something this helper cannot read: a fault of the calling code,
                // never of the design and never a crash.
                out = Json.write(designFault(id, "request", "could not read the request: " + e.getMessage()));
            } catch (Throwable t) {
                System.err.println("RocketSim: helper bug while answering a request");
                t.printStackTrace(System.err);
                out = Json.write(internal(id, "helper bug: " + describe(t)));
            }
            reply.print(out);
            reply.print('\n');
            reply.flush();
        }
        reply.flush();
        System.exit(0);
    }

    static void boot() throws Exception {
        // Keep OpenRocket's user-motor search away from the user's folders (and from creating them).
        MemoryPrefsFactory.USER.node("OpenRocket-core").put("UserThrustCurves", "");
        installDeterministicRandom();
        quietLogging();
        // OpenRocket's core module does not bind the part-preset lookup that the file reader
        // needs (the desktop module does); point it at the core preset database.
        OpenRocketCore.initialize(new info.openrocket.core.plugin.PluginModule(), new com.google.inject.AbstractModule() {
            @Override
            protected void configure() {
                bind(info.openrocket.core.database.ComponentPresetDao.class)
                        .to(info.openrocket.core.database.ComponentPresetDatabase.class);
            }
        });
        // Wait for the motor database: a file loaded before it is ready would lose its motors.
        Field f = OpenRocketCore.getCoreModule().getClass().getDeclaredField("motorLoader");
        f.setAccessible(true);
        Object loader = f.get(OpenRocketCore.getCoreModule());
        loader.getClass().getMethod("blockUntilLoaded").invoke(loader);
        Field p = OpenRocketCore.getCoreModule().getClass().getDeclaredField("presetLoader");
        p.setAccessible(true);
        Object presets = p.get(OpenRocketCore.getCoreModule());
        presets.getClass().getMethod("blockUntilLoaded").invoke(presets);
        Application.getPreferences();
    }

    /** Only warnings and errors from OpenRocket's logging, and only on standard error. */
    static void quietLogging() {
        try {
            org.slf4j.Logger root = org.slf4j.LoggerFactory.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME);
            if (root instanceof ch.qos.logback.classic.Logger) {
                ((ch.qos.logback.classic.Logger) root).setLevel(ch.qos.logback.classic.Level.WARN);
            }
        } catch (Throwable t) {
            System.err.println("RocketSim: could not lower the log level: " + t);
        }
    }

    static Map<String, Object> ping(Object id) {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("id", id);
        r.put("ok", true);
        r.put("openrocket", info.openrocket.core.util.BuildProperties.getVersion());
        r.put("java", System.getProperty("java.version"));
        r.put("helper", HELPER_VERSION);
        int motors = 0;
        for (info.openrocket.core.database.motor.ThrustCurveMotorSet set : Application.getThrustCurveMotorSetDatabase().getMotorSets()) {
            motors += set.getMotors().size();
        }
        r.put("motor_database_size", motors);
        return r;
    }

    /** Every motor in OpenRocket's built-in motor list, sorted by digest. */
    static Map<String, Object> motors(Object id) {
        List<Map<String, Object>> list = new ArrayList<>();
        for (info.openrocket.core.database.motor.ThrustCurveMotorSet set : Application.getThrustCurveMotorSetDatabase().getMotorSets()) {
            for (ThrustCurveMotor mo : set.getMotors()) {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("digest", mo.getDigest());
                m.put("manufacturer", mo.getManufacturer().getDisplayName());
                m.put("designation", mo.getDesignation());
                m.put("common_name", mo.getCommonName());
                m.put("diameter_m", num(mo.getDiameter()));
                m.put("length_m", num(mo.getLength()));
                m.put("total_impulse_ns", num(mo.getTotalImpulseEstimate()));
                list.add(m);
            }
        }
        list.sort((a, b) -> {
            int c = String.valueOf(a.get("digest")).compareTo(String.valueOf(b.get("digest")));
            return c != 0 ? c : String.valueOf(a.get("designation")).compareTo(String.valueOf(b.get("designation")));
        });
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("id", id);
        r.put("ok", true);
        r.put("motors", list);
        return r;
    }

    static Map<String, Object> internal(Object id, String message) {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("id", id);
        r.put("ok", false);
        r.put("error_kind", "internal");
        r.put("message", message);
        return r;
    }

    static Map<String, Object> designFault(Object id, String kind, String message) {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("id", id);
        r.put("ok", false);
        r.put("error_kind", kind);
        r.put("message", message);
        return r;
    }

    // ------------------------------------------------------------------ repeatability

    /**
     * OpenRocket gives every part that has no stored id a random UUID. Those ids key the
     * motor map, so with a random source the order of motors (and the numbers of cluster
     * and multi-stage flights) changes from load to load. This provider makes the
     * "random" bytes a fixed stream that is restarted before every load.
     */
    public static final class DetSpi extends java.security.SecureRandomSpi {
        static Random stream = new Random(0);
        static synchronized void reset(long seed) { stream = new Random(seed); }
        @Override protected void engineSetSeed(byte[] seed) { }
        @Override protected void engineNextBytes(byte[] bytes) { synchronized (DetSpi.class) { stream.nextBytes(bytes); } }
        @Override protected byte[] engineGenerateSeed(int n) { byte[] b = new byte[n]; engineNextBytes(b); return b; }
    }

    static final class DetProvider extends java.security.Provider {
        DetProvider() {
            super("RocketSimDet", "1.0", "repeatable random bytes for OpenRocket part ids");
            put("SecureRandom.RocketSimDet", DetSpi.class.getName());
        }
    }

    static void installDeterministicRandom() {
        java.security.Security.insertProviderAt(new DetProvider(), 1);
    }

    /**
     * SimulationOptions builds its wind models from a random seed when it is created, and
     * setRandomSeed() does not reach them. Replace them with models built from the flight's
     * seed (extra altitude levels get seed + 7919 * (level + 1)).
     */
    static void reseedWind(SimulationOptions opts, int seed) throws Exception {
        opts.setRandomSeed(seed);
        Field f = SimulationOptions.class.getDeclaredField("averageWindModel");
        f.setAccessible(true);
        f.set(opts, new PinkNoiseWindModel(seed));
        List<MultiLevelPinkNoiseWindModel.LevelWindModel> levels = opts.getMultiLevelWindModel().getLevels();
        Field mf = MultiLevelPinkNoiseWindModel.LevelWindModel.class.getDeclaredField("model");
        mf.setAccessible(true);
        for (int i = 0; i < levels.size(); i++) {
            PinkNoiseWindModel old = (PinkNoiseWindModel) mf.get(levels.get(i));
            PinkNoiseWindModel m = new PinkNoiseWindModel(seed + 7919 * (i + 1));
            m.setAverage(old.getAverage());
            m.setStandardDeviation(old.getStandardDeviation());
            m.setDirection(old.getDirection());
            mf.set(levels.get(i), m);
        }
    }

    // ------------------------------------------------------------------ run

    static final class RunRequest {
        String ork;
        String configId;
        double railM;
        double altitudeM = 0.0, latitudeDeg = 28.61, longitudeDeg = -80.6;
        double rodAngleDeg = 0.0, rodDirectionDeg = 90.0, windDirectionDeg = DEFAULT_WIND_DIRECTION_DEG;
        double turbulence = 0.1, timeStepS = 0.05;
        // Optional extras (PROTOCOL.md "Optional launch fields"); defaults are the reward's fixed choices.
        boolean launchIntoWind = false;
        GeodeticComputationStrategy geodetic = GeodeticComputationStrategy.SPHERICAL;
        Double baseTemperatureK = null, basePressurePa = null; // both null: standard ISA
        double maxSimTimeS = 1200.0;
        long maxSteps = 400000;
        /** Parity checks only: fly a motor OpenRocket swapped for another instead of failing the build. */
        boolean allowMotorSubstitution = false;
        List<double[]> flights = new ArrayList<>(); // {wind_ms, seed}
    }

    static RunRequest readRun(Map<String, Object> req) throws BadRequest {
        RunRequest r = new RunRequest();
        r.ork = reqString(req, "ork");
        Object cfg = req.get("config_id");
        if (cfg != null) {
            if (!(cfg instanceof String)) throw new BadRequest("config_id must be a string");
            r.configId = (String) cfg;
        }
        Object subst = req.get("allow_motor_substitution");
        if (subst != null) {
            if (!(subst instanceof Boolean)) throw new BadRequest("allow_motor_substitution must be true or false");
            r.allowMotorSubstitution = (Boolean) subst;
        }
        r.railM = reqNumber(req, "rail_m", null);
        if (!(r.railM > 0)) throw new BadRequest("rail_m must be above 0");
        Object launch = req.get("launch");
        if (launch != null) {
            if (!(launch instanceof Map)) throw new BadRequest("launch must be an object");
            @SuppressWarnings("unchecked")
            Map<String, Object> l = (Map<String, Object>) launch;
            for (String k : l.keySet()) {
                switch (k) {
                    case "altitude_m": case "latitude_deg": case "longitude_deg": case "rod_angle_deg":
                    case "rod_direction_deg": case "wind_turbulence": case "time_step_s": case "wind_direction_deg":
                    case "launch_into_wind": case "geodetic": case "base_temperature_k": case "base_pressure_pa":
                        break;
                    default: throw new BadRequest("unknown launch field " + Json.write(k));
                }
            }
            r.altitudeM = reqNumber(l, "altitude_m", r.altitudeM);
            r.latitudeDeg = reqNumber(l, "latitude_deg", r.latitudeDeg);
            r.longitudeDeg = reqNumber(l, "longitude_deg", r.longitudeDeg);
            r.rodAngleDeg = reqNumber(l, "rod_angle_deg", r.rodAngleDeg);
            r.rodDirectionDeg = reqNumber(l, "rod_direction_deg", r.rodDirectionDeg);
            r.windDirectionDeg = reqNumber(l, "wind_direction_deg", r.windDirectionDeg);
            r.turbulence = reqNumber(l, "wind_turbulence", r.turbulence);
            r.timeStepS = reqNumber(l, "time_step_s", r.timeStepS);
            Object into = l.get("launch_into_wind");
            if (into != null) {
                if (!(into instanceof Boolean)) throw new BadRequest("launch_into_wind must be true or false");
                r.launchIntoWind = (Boolean) into;
            }
            Object geo = l.get("geodetic");
            if (geo != null) {
                if (!(geo instanceof String)) throw new BadRequest("geodetic must be a string");
                switch ((String) geo) {
                    case "spherical": r.geodetic = GeodeticComputationStrategy.SPHERICAL; break;
                    case "flat": r.geodetic = GeodeticComputationStrategy.FLAT; break;
                    case "wgs84": r.geodetic = GeodeticComputationStrategy.WGS84; break;
                    default: throw new BadRequest("geodetic must be spherical, flat or wgs84");
                }
            }
            if (l.get("base_temperature_k") != null || l.get("base_pressure_pa") != null) {
                r.baseTemperatureK = reqNumber(l, "base_temperature_k", 288.15);
                r.basePressurePa = reqNumber(l, "base_pressure_pa", 101325.0);
                if (!(r.baseTemperatureK > 0) || !(r.basePressurePa > 0))
                    throw new BadRequest("base_temperature_k and base_pressure_pa must be above 0");
            }
        }
        if (!(r.timeStepS > 0)) throw new BadRequest("time_step_s must be above 0");
        if (!(r.turbulence >= 0)) throw new BadRequest("wind_turbulence must be 0 or more");
        r.maxSimTimeS = reqNumber(req, "max_sim_time_s", r.maxSimTimeS);
        if (!(r.maxSimTimeS > 0)) throw new BadRequest("max_sim_time_s must be above 0");
        double steps = reqNumber(req, "max_steps", (double) r.maxSteps);
        if (!(steps >= 1) || steps != Math.floor(steps)) throw new BadRequest("max_steps must be a whole number of 1 or more");
        r.maxSteps = (long) steps;
        Object fl = req.get("flights");
        if (!(fl instanceof List)) throw new BadRequest("flights must be a list");
        for (Object o : (List<?>) fl) {
            if (!(o instanceof Map)) throw new BadRequest("each flight must be an object");
            @SuppressWarnings("unchecked")
            Map<String, Object> m = (Map<String, Object>) o;
            double wind = reqNumber(m, "wind_ms", null);
            if (!(wind >= 0)) throw new BadRequest("wind_ms must be 0 or more");
            double seed = reqNumber(m, "seed", null);
            if (seed != Math.floor(seed) || Math.abs(seed) > Integer.MAX_VALUE) throw new BadRequest("seed must be a whole number that fits in 32 bits");
            r.flights.add(new double[] {wind, seed});
        }
        return r;
    }

    static String reqString(Map<String, Object> m, String key) throws BadRequest {
        Object v = m.get(key);
        if (!(v instanceof String)) throw new BadRequest(key + " must be a string");
        return (String) v;
    }

    static double reqNumber(Map<String, Object> m, String key, Double fallback) throws BadRequest {
        Object v = m.get(key);
        if (v == null) {
            if (fallback == null) throw new BadRequest(key + " is missing");
            return fallback;
        }
        if (!(v instanceof Number)) throw new BadRequest(key + " must be a number");
        double d = ((Number) v).doubleValue();
        if (Double.isNaN(d) || Double.isInfinite(d)) throw new BadRequest(key + " must be a finite number");
        return d;
    }

    /** Thrown for a fault of the design (not of this helper) while building or configuring it. */
    static final class BuildFault extends Exception {
        List<String> warnings;
        List<Map<String, Object>> motorLookup;
        BuildFault(String m) { super(m); }
    }

    static final class Loaded {
        OpenRocketDocument doc;
        Rocket rocket;
        FlightConfiguration config;
        List<String> warnings = new ArrayList<>();
        /** Per-motor report (motorLookup), or null when it could not be made. */
        List<Map<String, Object>> motorLookup;
        IdentityHashMap<RocketComponent, Map<String, Object>> lookupByMount = new IdentityHashMap<>();
        /** Some motor that flies is not the one the file names (only possible with allow_motor_substitution). */
        boolean motorSubstituted = false;
    }

    /** One motor element of the file, as written: {configid, manufacturer, designation, digest}. */
    static final class FileMotor {
        String configId, manufacturer, designation, digest;
    }

    /**
     * The motor elements of the file (plain, zipped or gzipped XML), one list per motormount
     * element in file order; the k-th list belongs to the k-th motor mount in OpenRocket's tree
     * order. Null when the file cannot be read this way (OpenRocket itself has already read it
     * by then, so null only switches the per-motor report off).
     */
    static List<List<FileMotor>> fileMotors(File file) {
        List<List<FileMotor>> out = new ArrayList<>();
        try (InputStream raw = new BufferedInputStream(new FileInputStream(file))) {
            raw.mark(4);
            int b0 = raw.read(), b1 = raw.read();
            raw.reset();
            InputStream xml = raw;
            if (b0 == 'P' && b1 == 'K') {
                ZipInputStream zip = new ZipInputStream(raw);
                ZipEntry e;
                boolean found = false;
                while ((e = zip.getNextEntry()) != null) {
                    if (!e.isDirectory() && e.getName().toLowerCase(Locale.ROOT).endsWith(".ork")) { found = true; break; }
                }
                if (!found) return null;
                xml = zip;
            } else if (b0 == 0x1f && b1 == 0x8b) {
                xml = new GZIPInputStream(raw);
            }
            SAXParserFactory f = SAXParserFactory.newInstance();
            f.setNamespaceAware(false);
            try { f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true); } catch (Exception ignored) { }
            SAXParser p = f.newSAXParser();
            p.parse(new InputSource(xml), new DefaultHandler() {
                final List<String> path = new ArrayList<>();
                final StringBuilder text = new StringBuilder();
                FileMotor current = null;
                @Override public void startElement(String uri, String local, String q, Attributes a) {
                    int n = path.size();
                    if ("motormount".equals(q)) out.add(new ArrayList<>());
                    if ("motor".equals(q) && n >= 1 && "motormount".equals(path.get(n - 1)) && !out.isEmpty()) {
                        current = new FileMotor();
                        current.configId = a.getValue("configid");
                        out.get(out.size() - 1).add(current);
                    }
                    path.add(q);
                    text.setLength(0);
                }
                @Override public void characters(char[] ch, int start, int len) { text.append(ch, start, len); }
                @Override public void endElement(String uri, String local, String q) {
                    int n = path.size();
                    if (current != null && n >= 2 && "motor".equals(path.get(n - 2))) {
                        String v = text.toString().trim();
                        if ("digest".equals(q)) current.digest = v.isEmpty() ? null : v;
                        else if ("manufacturer".equals(q)) current.manufacturer = v;
                        else if ("designation".equals(q)) current.designation = v;
                    }
                    if ("motor".equals(q)) current = null;
                    path.remove(n - 1);
                    text.setLength(0);
                }
            });
        } catch (Exception e) {
            System.err.println("RocketSim: could not read the motor elements of " + file + ": " + e);
            return null;
        }
        return out;
    }

    /**
     * How OpenRocket found each motor of the flown configuration, one entry per motor mount
     * that the file gives a motor for in that configuration (PROTOCOL.md "motor_lookup"):
     * found_by "digest" (the thrust curve the file names), "name" (no curve with that digest,
     * or the file named none, so OpenRocket took a motor of the same maker and designation,
     * which can fly a different thrust curve) or "none" (OpenRocket found no such motor and the
     * mount flies empty). Null when the file's motor elements cannot be matched to the mounts.
     */
    static List<Map<String, Object>> motorLookup(File file, Rocket rocket, FlightConfiguration cfg,
                                                 IdentityHashMap<RocketComponent, Map<String, Object>> byMount) {
        List<List<FileMotor>> written = fileMotors(file);
        if (written == null) return null;
        List<RocketComponent> mounts = new ArrayList<>();
        Iterator<RocketComponent> it = rocket.iterator(false);
        while (it.hasNext()) {
            RocketComponent c = it.next();
            if (c instanceof MotorMount && ((MotorMount) c).isMotorMount()) mounts.add(c);
        }
        if (mounts.size() != written.size()) {
            System.err.println("RocketSim: " + written.size() + " motormount elements but " + mounts.size()
                    + " motor mounts; no per-motor report");
            return null;
        }
        List<Map<String, Object>> out = new ArrayList<>();
        for (int k = 0; k < mounts.size(); k++) {
            RocketComponent c = mounts.get(k);
            FileMotor fm = null;
            for (FileMotor x : written.get(k)) {
                if (x.configId != null && new FlightConfigurationId(x.configId).equals(cfg.getId())) { fm = x; break; }
            }
            if (fm == null) continue; // the file gives this mount no motor in the flown configuration
            MotorConfiguration mc = ((MotorMount) c).getMotorConfig(cfg.getId());
            Motor mo = mc == null || mc.isEmpty() ? null : mc.getMotor();
            Map<String, Object> e = new LinkedHashMap<>();
            e.put("mount", String.valueOf(c.getName()));
            e.put("requested_manufacturer", fm.manufacturer);
            e.put("requested_designation", fm.designation);
            e.put("requested_digest", fm.digest);
            String foundBy;
            if (mo == null) foundBy = "none";
            else if (fm.digest != null && fm.digest.equals(mo.getDigest())) foundBy = "digest";
            else foundBy = "name";
            e.put("found_by", foundBy);
            e.put("substituted", mo != null && fm.digest != null && !fm.digest.equals(mo.getDigest()));
            e.put("flown_manufacturer", mo instanceof ThrustCurveMotor ? ((ThrustCurveMotor) mo).getManufacturer().getDisplayName() : null);
            e.put("flown_designation", mo == null ? null : mo.getDesignation());
            e.put("flown_digest", mo == null ? null : mo.getDigest());
            out.add(e);
            byMount.put(c, e);
        }
        return out;
    }

    /** Load the file with the fixed part-id seed and pick the flown configuration. */
    static Loaded load(RunRequest r) throws Exception {
        File file = new File(r.ork);
        if (!file.isFile()) throw new LoadFault("file not found: " + r.ork);
        Loaded L = new Loaded();
        GeneralRocketLoader loader;
        synchronized (DetSpi.class) { DetSpi.reset(PART_ID_SEED); }
        try {
            loader = new GeneralRocketLoader(file);
            L.doc = loader.load();
        } catch (Throwable t) {
            if (isHelperBug(t)) throw t;
            throw new LoadFault(describe(t));
        }
        TreeSet<String> ws = new TreeSet<>();
        List<String> invalid = new ArrayList<>(), missingMotors = new ArrayList<>(), swappedMotors = new ArrayList<>();
        for (Object w : loader.getWarnings()) {
            String text = plain(String.valueOf(w));
            ws.add(text);
            if (text.startsWith(INVALID_PARAMETER_WARNING)) invalid.add(text);
            else if (w instanceof info.openrocket.core.logging.Warning.MissingMotor) missingMotors.add(text);
            else if (text.contains("has differing thrust curve") || text.contains("one chosen arbitrarily")) swappedMotors.add(text);
        }
        L.warnings.addAll(ws);
        try {
            // OpenRocket skips a value it cannot read (for example NaN) and keeps its default, so
            // the rocket it would fly is not the one written in the file.
            if (!invalid.isEmpty()) {
                throw new BuildFault("OpenRocket could not read some values in the file and would fly a different rocket: "
                        + String.join("; ", invalid));
            }
            L.rocket = L.doc.getRocket();
            if (L.rocket == null) throw new BuildFault("the file holds no rocket");
            FlightConfiguration cfg;
            if (r.configId != null) {
                FlightConfigurationId fcid = new FlightConfigurationId(r.configId);
                if (!L.rocket.containsFlightConfigurationID(fcid)) throw new BuildFault("the rocket has no flight configuration " + r.configId);
                cfg = L.rocket.getFlightConfiguration(fcid);
            } else {
                cfg = L.rocket.getSelectedConfiguration();
            }
            if (cfg == null) throw new BuildFault("the rocket has no flight configuration");
            // Fly the whole rocket: stages switched off in the editor's view are switched on again.
            cfg.setAllStages();
            L.rocket.setSelectedConfiguration(cfg.getId());
            L.motorLookup = motorLookup(file, L.rocket, cfg, L.lookupByMount);
            // A motor OpenRocket could not find at all: the mount would fly empty. With the
            // per-motor report only motors of the flown configuration count; without it, any
            // missing-motor warning does.
            List<String> notFound = new ArrayList<>();
            if (L.motorLookup != null) {
                for (Map<String, Object> e : L.motorLookup) {
                    if ("none".equals(e.get("found_by"))) notFound.add(e.get("requested_manufacturer") + " " + e.get("requested_designation"));
                }
            } else {
                notFound.addAll(missingMotors);
            }
            if (!notFound.isEmpty() && !r.allowMotorSubstitution) {
                throw new BuildFault("a motor in the file is not in OpenRocket " + OPENROCKET_VERSION
                        + "'s motor list, so its mount would fly empty (" + String.join(", ", notFound) + ")"
                        + (missingMotors.isEmpty() ? "" : ": " + String.join("; ", missingMotors)));
            }
            if (!cfg.hasMotors() || cfg.getActiveMotors().isEmpty()) {
                List<String> withMotors = new ArrayList<>();
                for (FlightConfigurationId other : L.rocket.getIds()) {
                    if (L.rocket.hasMotors(other)) withMotors.add(other.key.toString());
                }
                throw new BuildFault("no motor in the flown configuration " + cfg.getId().key
                        + (withMotors.isEmpty() ? " (no configuration of this rocket has a motor)"
                                : " (configurations with motors: " + String.join(", ", withMotors) + ")"));
            }
            // A motor whose thrust-curve digest is not in OpenRocket's list is replaced by another
            // motor of the same maker and designation, which can be a different motor. Every
            // motor that flies must be one whose digest the file names.
            List<String> swapped = new ArrayList<>();
            if (L.motorLookup != null) {
                for (Map<String, Object> e : L.motorLookup) {
                    if (Boolean.TRUE.equals(e.get("substituted"))) {
                        swapped.add(e.get("requested_manufacturer") + " " + e.get("requested_designation")
                                + " flies as " + e.get("flown_manufacturer") + " " + e.get("flown_designation"));
                    }
                }
            } else {
                for (String w : swappedMotors) if (w.contains("has differing thrust curve")) swapped.add(w);
            }
            L.motorSubstituted = !swapped.isEmpty();
            if (!swapped.isEmpty() && !r.allowMotorSubstitution) {
                throw new BuildFault("a motor in the file is not in OpenRocket " + OPENROCKET_VERSION
                        + "'s motor list, so OpenRocket would fly another thrust curve in its place ("
                        + String.join(", ", swapped) + ")"
                        + (swappedMotors.isEmpty() ? "" : ": " + String.join("; ", swappedMotors)));
            }
            L.config = cfg;
        } catch (BuildFault e) {
            e.warnings = L.warnings;
            e.motorLookup = L.motorLookup;
            throw e;
        } catch (Throwable t) {
            if (isHelperBug(t)) throw t;
            BuildFault e = new BuildFault(describe(t));
            e.warnings = L.warnings;
            e.motorLookup = L.motorLookup;
            throw e;
        }
        return L;
    }

    static final class LoadFault extends Exception {
        LoadFault(String m) { super(m); }
    }

    static Map<String, Object> run(Object id, Map<String, Object> raw) throws Throwable {
        RunRequest r = readRun(raw);
        Loaded L;
        try {
            L = load(r);
        } catch (LoadFault e) {
            return designFault(id, "load", e.getMessage());
        } catch (BuildFault e) {
            Map<String, Object> fault = designFault(id, "build", e.getMessage());
            fault.put("load_warnings", e.warnings);
            fault.put("motor_lookup", e.motorLookup);
            return fault;
        }
        Map<String, Object> rocketInfo;
        List<Object> components;
        try {
            rocketInfo = rocketSummary(L);
            components = componentList(L);
        } catch (Throwable t) {
            if (isHelperBug(t)) throw t;
            Map<String, Object> fault = designFault(id, "build", describe(t));
            fault.put("load_warnings", L.warnings);
            return fault;
        }
        // A rocket without a finite mass, balance point or centre of pressure cannot fly; OpenRocket
        // would stop at its first step with an internal error.
        List<String> notFinite = new ArrayList<>();
        for (String key : new String[] {"mass_kg", "cg_m", "cp_m"}) {
            if (rocketInfo.get(key) == null) notFinite.add(key);
        }
        if (!notFinite.isEmpty()) {
            Map<String, Object> fault = designFault(id, "build", "OpenRocket computed no finite value for "
                    + String.join(", ", notFinite) + " of this rocket (a size, mass or density is not a usable number)");
            fault.put("load_warnings", L.warnings);
            return fault;
        }
        rocketInfo.put("motor_substituted", L.motorSubstituted);
        List<Object> flights = new ArrayList<>();
        for (double[] f : r.flights) flights.add(fly(r, f[0], (int) f[1]));

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", id);
        out.put("ok", true);
        out.put("load_warnings", L.warnings);
        out.put("motor_lookup", L.motorLookup);
        out.put("rocket", rocketInfo);
        out.put("components", components);
        out.put("flights", flights);
        return out;
    }

    // ------------------------------------------------------------------ geometry and mass

    /**
     * Whole-rocket numbers for the flown configuration with every stage attached:
     * length_m      OpenRocket's aerodynamic length of the configuration (nose tip to the aft-most body or fin end)
     * max_diameter_m  twice the largest outer radius of any body part (nose cones, tubes, transitions, also in pods)
     * mass_kg       launch mass (structure, motors and propellant), from OpenRocket's mass calculator
     * dry_mass_kg   burnout mass (structure and empty motor cases, no propellant)
     * structure_mass_kg  structure only, no motors (extra field)
     * cg_m          launch centre of gravity from the nose tip
     * cp_m          centre of pressure from OpenRocket's Barrowman calculator at Mach 0.3, zero angle of attack, no roll
     * stability_cal (cp_m - cg_m) / OpenRocket's reference length (the configuration's reference diameter)
     * motor_count   number of motors that fly (cluster and pod copies counted)
     * total_impulse_ns  sum of the motors' total impulse (each copy counted)
     */
    static Map<String, Object> rocketSummary(Loaded L) {
        FlightConfiguration cfg = L.config;
        Map<String, Object> m = new LinkedHashMap<>();
        double maxR = 0;
        for (RocketComponent c : cfg.getActiveComponents()) {
            if (c instanceof SymmetricComponent) {
                maxR = Math.max(maxR, ((SymmetricComponent) c).getMaxRadius());
            }
        }
        RigidBody launch = MassCalculator.calculateLaunch(cfg);
        RigidBody burnout = MassCalculator.calculateBurnout(cfg);
        RigidBody structure = MassCalculator.calculateStructure(cfg);
        BarrowmanCalculator calc = new BarrowmanCalculator();
        FlightConditions fc = new FlightConditions(cfg);
        fc.setMach(STATIC_CP_MACH);
        fc.setAOA(0);
        fc.setRollRate(0);
        Coordinate cp = calc.getCP(cfg, fc, new WarningSet());
        double ref = cfg.getReferenceLength();
        int motors = 0;
        double impulse = 0;
        for (MotorConfiguration mc : sortedMotors(cfg)) {
            int n = mc.getMount().getComponentLocations().length;
            motors += n;
            impulse += n * mc.getMotor().getTotalImpulseEstimate();
        }
        m.put("length_m", num(cfg.getLengthAerodynamic()));
        m.put("max_diameter_m", num(2 * maxR));
        m.put("stage_count", cfg.getActiveStageCount());
        m.put("mass_kg", num(launch.getMass()));
        m.put("dry_mass_kg", num(burnout.getMass()));
        m.put("structure_mass_kg", num(structure.getMass()));
        m.put("cg_m", num(launch.getCM().x));
        m.put("cp_m", num(cp.x));
        m.put("stability_cal", num(ref > 0 ? (cp.x - launch.getCM().x) / ref : Double.NaN));
        m.put("reference_length_m", num(ref));
        m.put("motor_count", motors);
        m.put("total_impulse_ns", num(impulse));
        m.put("config_id", cfg.getId().key.toString());
        return m;
    }

    /** Active motors in a fixed order (by position, then mount name), so nothing depends on hash order. */
    static List<MotorConfiguration> sortedMotors(FlightConfiguration cfg) {
        List<MotorConfiguration> list = new ArrayList<>();
        for (MotorConfiguration mc : cfg.getActiveMotors()) if (mc != null && mc.getMotor() != null) list.add(mc);
        list.sort((a, b) -> {
            int c = Double.compare(xFront((RocketComponent) a.getMount()), xFront((RocketComponent) b.getMount()));
            if (c != 0) return c;
            return String.valueOf(((RocketComponent) a.getMount()).getName()).compareTo(String.valueOf(((RocketComponent) b.getMount()).getName()));
        });
        return list;
    }

    /** Smallest x (from the nose tip) of any copy of the part, as OpenRocket placed it. */
    static double xFront(RocketComponent c) {
        double x = Double.NaN;
        for (Coordinate k : c.getComponentLocations()) x = Double.isNaN(x) ? k.x : Math.min(x, k.x);
        return x;
    }

    /**
     * How far the part's own axis lies from the rocket's centre line: the smallest distance over
     * its copies (0 for a part on the centre line; a pod or side booster and everything in it
     * report the pod's distance).
     */
    static double axisOffset(RocketComponent c) {
        double r = Double.NaN;
        for (Coordinate k : c.getComponentLocations()) {
            double d = Math.hypot(k.y, k.z);
            r = Double.isNaN(r) ? d : Math.min(r, d);
        }
        return r;
    }

    /** Mean x of all copies of the part. */
    static double xMean(RocketComponent c) {
        Coordinate[] locs = c.getComponentLocations();
        if (locs.length == 0) return Double.NaN;
        double s = 0;
        for (Coordinate k : locs) s += k.x;
        return s / locs.length;
    }

    /**
     * Every part except the Rocket itself, in OpenRocket's tree order. Top-level stages have
     * parent -1. Masses are for the part alone (children not included, motors not included),
     * as OpenRocket's getComponentMass reports it; cg_x_m is from the nose tip, averaged over
     * the part's copies.
     */
    static List<Object> componentList(Loaded L) {
        FlightConfiguration cfg = L.config;
        FlightConfigurationId fcid = cfg.getId();
        List<RocketComponent> all = new ArrayList<>();
        Iterator<RocketComponent> it = L.rocket.iterator(false);
        while (it.hasNext()) all.add(it.next());
        IdentityHashMap<RocketComponent, Integer> index = new IdentityHashMap<>();
        for (int i = 0; i < all.size(); i++) index.put(all.get(i), i);
        List<Object> out = new ArrayList<>();
        for (int i = 0; i < all.size(); i++) {
            RocketComponent c = all.get(i);
            Map<String, Object> m = new LinkedHashMap<>();
            Integer parent = c.getParent() == null ? null : index.get(c.getParent());
            m.put("index", i);
            m.put("parent", parent == null ? -1 : parent);
            m.put("type", c.getClass().getSimpleName());
            m.put("name", String.valueOf(c.getName()));
            m.put("active", cfg.isComponentActive(c));
            m.put("stage", c.getStageNumber());
            m.put("instances", c.getComponentLocations().length);
            m.put("axis_offset_m", num(axisOffset(c)));
            double x0 = xFront(c);
            m.put("x0_m", num(x0));
            m.put("length_m", num(c.getLength()));
            Double rFore = null, rAft = null, rIn = null, thick = null, radialOffset = null;
            boolean filled = false;
            if (c instanceof SymmetricComponent) {
                SymmetricComponent s = (SymmetricComponent) c;
                rFore = s.getForeRadius();
                rAft = s.getAftRadius();
                filled = s.isFilled();
                thick = s.getThickness();
                if (c instanceof BodyTube) rIn = filled ? 0.0 : ((BodyTube) c).getInnerRadius();
            } else if (c instanceof RingComponent) {
                RingComponent rc = (RingComponent) c;
                rFore = rc.getOuterRadius();
                rAft = rc.getOuterRadius();
                rIn = rc.getInnerRadius();
                thick = rc.getThickness();
                radialOffset = rc.getRadialPosition();
            } else if (c instanceof Tube) {
                Tube t = (Tube) c;
                rFore = t.getOuterRadius();
                rAft = t.getOuterRadius();
                rIn = t.getInnerRadius();
                thick = t.getThickness();
            } else if (c instanceof RailButton) {
                RailButton b = (RailButton) c;
                rFore = b.getOuterDiameter() / 2;
                rAft = b.getOuterDiameter() / 2;
                rIn = b.getInnerDiameter() / 2;
            } else if (c instanceof MassObject) {
                MassObject mo = (MassObject) c;
                rFore = mo.getRadius();
                rAft = mo.getRadius();
                radialOffset = mo.getRadialPosition();
            } else if (c instanceof FinSet) {
                thick = ((FinSet) c).getThickness();
            }
            m.put("outer_radius_fore_m", num(rFore));
            m.put("outer_radius_aft_m", num(rAft));
            m.put("inner_radius_m", num(rIn));
            m.put("thickness_m", num(thick));
            m.put("filled", filled);
            m.put("radial_offset_m", num(radialOffset));
            double computedMass = c.getComponentMass();
            boolean massOver = c.isMassOverridden();
            m.put("mass_kg", num(massOver ? c.getOverrideMass() : computedMass));
            m.put("computed_mass_kg", num(computedMass));
            m.put("mass_overridden", massOver);
            double cgRel = c.getComponentCG().x;
            boolean cgOver = c.isCGOverridden();
            double xm = xMean(c);
            m.put("cg_x_m", num(xm + (cgOver ? c.getOverrideCGX() : cgRel)));
            m.put("computed_cg_x_m", num(xm + cgRel));
            m.put("cg_overridden", cgOver);
            m.put("cd_overridden", c.isCDOverridden());
            m.put("override_subcomponents", (massOver && c.isSubcomponentsOverriddenMass())
                    || (cgOver && c.isSubcomponentsOverriddenCG())
                    || (c.isCDOverridden() && c.isSubcomponentsOverriddenCD()));
            RocketComponent by = c.getMassOverriddenBy();
            m.put("mass_overridden_by", by == null || by == c ? null : index.get(by));
            m.put("fins", c instanceof FinSet ? fins((FinSet) c, x0) : null);
            m.put("motor", c instanceof MotorMount ? motor((MotorMount) c, fcid, x0, L.lookupByMount.get(c)) : null);
            m.put("recovery", c instanceof RecoveryDevice ? recovery((RecoveryDevice) c, fcid) : null);
            out.add(m);
        }
        return out;
    }

    /**
     * Fin numbers. root_chord_m is OpenRocket's fin length (root chord). For trapezoid fins
     * tip_chord_m and sweep_m come from OpenRocket directly; for other shapes they are read
     * from the outline: tip_chord_m is the length along the body of the outline at its
     * greatest height, sweep_m is the distance from the root's leading edge to the leading
     * point at that height. points are one fin's outline, x from the fin's leading root
     * point, y outward from the body.
     */
    static Map<String, Object> fins(FinSet f, double x0) {
        Map<String, Object> m = new LinkedHashMap<>();
        Coordinate[] pts = f.getFinPoints();
        double maxY = Double.NEGATIVE_INFINITY;
        for (Coordinate p : pts) maxY = Math.max(maxY, p.y);
        double tipLo = Double.POSITIVE_INFINITY, tipHi = Double.NEGATIVE_INFINITY;
        for (Coordinate p : pts) {
            if (Math.abs(p.y - maxY) <= 1e-9) { tipLo = Math.min(tipLo, p.x); tipHi = Math.max(tipHi, p.x); }
        }
        double rootLe = pts.length > 0 ? pts[0].x : Double.NaN;
        double tip, sweep;
        if (f instanceof TrapezoidFinSet) {
            tip = ((TrapezoidFinSet) f).getTipChord();
            sweep = ((TrapezoidFinSet) f).getSweep();
        } else {
            tip = pts.length > 0 ? tipHi - tipLo : Double.NaN;
            sweep = pts.length > 0 ? tipLo - rootLe : Double.NaN;
        }
        m.put("count", f.getFinCount());
        m.put("root_chord_m", num(f.getLength()));
        m.put("tip_chord_m", num(tip));
        m.put("span_m", num(f.getSpan()));
        m.put("sweep_m", num(sweep));
        m.put("thickness_m", num(f.getThickness()));
        m.put("cant_deg", num(Math.toDegrees(f.getCantAngle())));
        m.put("root_x0_m", num(x0));
        m.put("root_radius_m", num(f.getBodyRadius()));
        m.put("base_rotation_deg", num(Math.toDegrees(f.getBaseRotation())));
        List<Object> pl = new ArrayList<>();
        for (Coordinate p : pts) {
            List<Object> xy = new ArrayList<>();
            xy.add(num(p.x));
            xy.add(num(p.y));
            pl.add(xy);
        }
        m.put("points", pl);
        return m;
    }

    /**
     * Motor of the flown configuration in this mount, or null. x0_m is the motor's front end
     * from the nose tip: the mount's aft end plus the overhang, minus the motor length
     * (the rule OpenRocket uses to place motors), for the fore-most copy of the mount.
     * total_impulse_ns and burn_time_s are for one motor; count is the number of copies.
     */
    static Map<String, Object> motor(MotorMount mm, FlightConfigurationId fcid, double mountX0,
                                     Map<String, Object> lookup) {
        if (!mm.isMotorMount()) return null;
        MotorConfiguration mc = mm.getMotorConfig(fcid);
        if (mc == null || mc.isEmpty() || mc.getMotor() == null) return null;
        Motor mo = mc.getMotor();
        Map<String, Object> m = new LinkedHashMap<>();
        String maker = mo instanceof ThrustCurveMotor ? ((ThrustCurveMotor) mo).getManufacturer().getDisplayName() : null;
        m.put("manufacturer", maker);
        m.put("designation", mo.getDesignation());
        m.put("digest", mo.getDigest());
        m.put("diameter_m", num(mo.getDiameter()));
        m.put("length_m", num(mo.getLength()));
        double overhang = mm.getMotorOverhang();
        m.put("x0_m", num(mountX0 + mm.getLength() + overhang - mo.getLength()));
        m.put("overhang_m", num(overhang));
        m.put("total_impulse_ns", num(mo.getTotalImpulseEstimate()));
        m.put("burn_time_s", num(mo.getBurnTimeEstimate()));
        m.put("ignition_event", mc.getIgnitionEvent() == null ? null : mc.getIgnitionEvent().name());
        m.put("ignition_delay_s", num(mc.getIgnitionDelay()));
        m.put("ejection_delay_s", num(mc.getEjectionDelay()));
        m.put("launch_mass_kg", num(mo.getLaunchMass()));
        m.put("burnout_mass_kg", num(mo.getBurnoutMass()));
        m.put("count", ((RocketComponent) mm).getComponentLocations().length);
        // How OpenRocket found this motor (see motorLookup); null when the report could not be made.
        m.put("found_by", lookup == null ? null : lookup.get("found_by"));
        m.put("substituted", lookup == null ? null : lookup.get("substituted"));
        m.put("requested_manufacturer", lookup == null ? null : lookup.get("requested_manufacturer"));
        m.put("requested_designation", lookup == null ? null : lookup.get("requested_designation"));
        m.put("requested_digest", lookup == null ? null : lookup.get("requested_digest"));
        return m;
    }

    static Map<String, Object> recovery(RecoveryDevice rd, FlightConfigurationId fcid) {
        Map<String, Object> m = new LinkedHashMap<>();
        DeploymentConfiguration dc = rd.getDeploymentConfigurations().get(fcid);
        m.put("kind", rd instanceof Parachute ? "parachute" : rd instanceof Streamer ? "streamer" : rd.getClass().getSimpleName().toLowerCase(Locale.ROOT));
        m.put("diameter_m", num(rd instanceof Parachute ? ((Parachute) rd).getDiameter() : null));
        m.put("cd", num(rd.getCD()));
        m.put("area_m2", num(rd.getArea()));
        if (rd instanceof Streamer) {
            m.put("strip_length_m", num(((Streamer) rd).getStripLength()));
            m.put("strip_width_m", num(((Streamer) rd).getStripWidth()));
        }
        m.put("deploy_event", dc == null || dc.getDeployEvent() == null ? null : dc.getDeployEvent().name());
        m.put("deploy_altitude_m", num(dc == null ? null : dc.getDeployAltitude()));
        m.put("deploy_delay_s", num(dc == null ? null : dc.getDeployDelay()));
        return m;
    }

    // ------------------------------------------------------------------ flights

    /** Thrown by the step counter to stop a flight that used up its step budget. */
    static final class StepCapReached extends SimulationException {
        StepCapReached(String m) { super(m); }
    }

    /**
     * Counts integration steps over all branches (the engine may copy listeners for booster
     * branches; the copies share the counter) and records which branches carry a recovery
     * device. A flight that would take more than max_steps steps is stopped before the
     * next step, which makes the cap independent of how busy the machine is.
     */
    static final class StepCounter extends AbstractSimulationListener {
        final long[] steps;
        final long max;
        final IdentityHashMap<FlightDataBranch, Boolean> recoveryByBranch;
        final IdentityHashMap<FlightDataBranch, Integer> stagesSeen;

        StepCounter(long max) {
            this.max = max;
            this.steps = new long[1];
            this.recoveryByBranch = new IdentityHashMap<>();
            this.stagesSeen = new IdentityHashMap<>();
        }

        @Override
        public boolean preStep(SimulationStatus status) throws SimulationException {
            if (steps[0] >= max) throw new StepCapReached("the flight used all " + max + " steps");
            steps[0]++;
            // Which branch carries a recovery device: checked again whenever the attached stages change.
            FlightDataBranch b = status.getFlightDataBranch();
            FlightConfiguration cfg = status.getConfiguration();
            int stages = cfg.getActiveStageCount();
            Integer seen = stagesSeen.get(b);
            if (seen == null || seen != stages) {
                stagesSeen.put(b, stages);
                boolean has = false;
                for (RocketComponent c : cfg.getActiveComponents()) if (c instanceof RecoveryDevice) { has = true; break; }
                recoveryByBranch.put(b, has);
            }
            return true;
        }

        @Override
        public boolean isSystemListener() { return false; }
    }

    static Map<String, Object> fly(RunRequest r, double windMs, int seed) throws Throwable {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("wind_ms", num(windMs));
        m.put("seed", seed);
        Loaded L;
        try {
            L = load(r);
        } catch (LoadFault e) {
            return failedFlight(m, "load", e.getMessage());
        } catch (BuildFault e) {
            return failedFlight(m, "build", e.getMessage());
        }
        Simulation sim;
        StepCounter counter = new StepCounter(r.maxSteps);
        String exception = null;
        boolean stepCap = false;
        try {
            sim = new Simulation(L.doc, L.rocket);
            sim.setFlightConfigurationId(L.config.getId());
            SimulationOptions o = sim.getOptions();
            reseedWind(o, seed);
            o.setWindModelType(WindModelType.AVERAGE);
            o.setLaunchRodLength(r.railM);
            o.setLaunchIntoWind(r.launchIntoWind);
            o.setLaunchRodAngle(Math.toRadians(r.rodAngleDeg));
            o.setLaunchRodDirection(Math.toRadians(r.rodDirectionDeg));
            o.setWindSpeedAverage(windMs);
            o.setWindTurbulenceIntensity(r.turbulence);
            o.setWindDirection(Math.toRadians(r.windDirectionDeg));
            o.setLaunchAltitude(r.altitudeM);
            o.setLaunchLatitude(r.latitudeDeg);
            o.setLaunchLongitude(r.longitudeDeg);
            o.setGeodeticComputation(r.geodetic);
            if (r.baseTemperatureK == null) {
                o.setISAAtmosphere(true);
            } else {
                o.setISAAtmosphere(false);
                o.setLaunchTemperature(r.baseTemperatureK);
                o.setLaunchPressure(r.basePressurePa);
            }
            o.setTimeStep(r.timeStepS);
            o.setMaxSimulationTime(r.maxSimTimeS);
            o.setMaximumStepAngle(Math.toRadians(3.0));
        } catch (Throwable t) {
            if (isHelperBug(t)) throw t;
            return failedFlight(m, "build", "could not set up the flight: " + describe(t));
        }
        try {
            sim.simulate(counter);
        } catch (StepCapReached e) {
            stepCap = true;
        } catch (Throwable t) {
            for (Throwable c = t; c != null; c = c.getCause() == c ? null : c.getCause()) {
                if (c instanceof StepCapReached) stepCap = true;
            }
            if (!stepCap) {
                if (isHelperBug(t)) throw t;
                exception = describe(t);
            }
        }
        if (exception != null) {
            // OpenRocket itself failed during the flight (for example a not-a-number value). Its
            // partial numbers are artefacts of the failure, not a flight: no numbers are reported.
            m.put("steps", counter.steps[0]);
            return failedFlight(m, "crash", "OpenRocket failed during the flight: " + plain(exception));
        }
        FlightData d = sim.getSimulatedData();
        if (d == null || d.getBranchCount() == 0 || d.getBranch(0).getLength() == 0) {
            // Nothing failed, the rocket simply never started flying (for example a motor that
            // ignites only after max_sim_time_s). Repeatable and a fault of the design.
            m.put("steps", counter.steps[0]);
            return failedFlight(m, "build", "OpenRocket produced no flight data: the rocket never started flying "
                    + "(check the motor's ignition event and delay)");
        }
        fillFlight(m, d, counter, r, stepCap);
        return m;
    }

    /**
     * A flight without numbers. kind: "load" or "build" (the file reloaded for this flight failed,
     * or the rocket never started flying) or "crash" (OpenRocket threw an error while flying).
     */
    static Map<String, Object> failedFlight(Map<String, Object> m, String kind, String error) {
        m.put("ok", false);
        m.put("error_kind", kind);
        m.put("error", error);
        return m;
    }

    /**
     * Flight numbers, all read from OpenRocket's flight data (branch 0 is the part that
     * carries the nose cone; other branches are dropped boosters):
     *
     * apogee_m, max_velocity_ms, max_accel_ms2, max_mach, time_to_apogee_s, flight_time_s,
     * ground_hit_ms: OpenRocket's own summary values (FlightData), which it computes from branch 0.
     * rail_exit_ms: OpenRocket's launch-rod velocity (total speed at the LAUNCHROD event of branch 0).
     * stability_rail_cal: TYPE_STABILITY at the first sample of branch 0 at or after the LAUNCHROD
     *   event that holds a finite value.
     * stability_min_burn_cal: the lowest finite TYPE_STABILITY of branch 0 from the LAUNCHROD event
     *   to the last BURNOUT event of branch 0, both ends included; equal to stability_rail_cal
     *   when no sample lies in that window (for example burnout before rail exit).
     * burnout_time_s: time of the last BURNOUT event of branch 0.
     * ignition_time_s: time of the first IGNITION event of branch 0 (0 for a rocket whose motor lights
     *   at launch; later when the first motor lights only after a delay, while the rocket waits on the pad).
     * liftoff_twr: mean of TYPE_THRUST_WEIGHT_RATIO (thrust / (mass * gravity)) over the rail phase,
     *   from the LIFTOFF event to the LAUNCHROD event of branch 0, weighted by time (trapezoid rule
     *   over the samples in that window). When the rocket never leaves the rail, the window ends at
     *   the last BURNOUT, or at the last sample.
     * per branch: deployed / deploy_time_s from its first RECOVERY_DEVICE_DEPLOYMENT event;
     *   deployments lists every such event (device name, time, speed, during_burn) in time order;
     *   the speed of one opening is TYPE_VELOCITY_TOTAL of that branch at that time (linear
     *   interpolation between the two samples around it); deploy_speed_ms is the largest of them
     *   (the fastest opening, usually the main of a dual-deploy rocket); deploy_during_burn is true
     *   when, at the time of any opening, some motor mount of the branch had an IGNITION event at
     *   or before it and no BURNOUT event at or before it; landed / landing_time_s from its
     *   GROUND_HIT event; landing_vertical_ms is -TYPE_VELOCITY_Z and landing_total_ms is
     *   TYPE_VELOCITY_TOTAL at the branch's touchdown sample (groundHitSample: the sample at its
     *   first GROUND_HIT event, which is not always the last sample, because OpenRocket may keep
     *   simulating a branch that landed while a motor burns; null when the branch did not land).
     * hit_time_cap: some branch did not land although nothing else stopped it (no abort, no
     *   step cap), so it was stopped by max_sim_time_s.
     * A flight during which OpenRocket threw an error never gets here: it is a failed flight.
     */
    static void fillFlight(Map<String, Object> m, FlightData d, StepCounter counter, RunRequest r,
                           boolean stepCap) {
        FlightDataBranch main = d.getBranch(0);
        String abort = null;
        for (FlightDataBranch b : d.getBranches()) {
            for (FlightEvent e : b.getEvents()) {
                if (e.getType() == FlightEvent.Type.SIM_ABORT && abort == null) {
                    Object data = e.getData();
                    abort = plain(data instanceof Message ? ((Message) data).getMessageDescription() : String.valueOf(data));
                }
            }
        }

        double rod = firstEventTime(main, FlightEvent.Type.LAUNCHROD);
        double liftoff = firstEventTime(main, FlightEvent.Type.LIFTOFF);
        double burnout = lastEventTime(main, FlightEvent.Type.BURNOUT);
        List<Double> t = main.get(FlightDataType.TYPE_TIME);
        List<Double> stab = main.get(FlightDataType.TYPE_STABILITY);
        double atRail = Double.NaN, minBurn = Double.NaN;
        if (t != null && stab != null && !t.isEmpty() && !Double.isNaN(rod)) {
            // With no BURNOUT event (the flight stopped while a motor burned) the window runs to the last sample.
            double burnEnd = !Double.isNaN(burnout) ? burnout : t.get(t.size() - 1);
            for (int i = 0; i < Math.min(t.size(), stab.size()); i++) {
                double ti = t.get(i), si = val(stab.get(i));
                if (ti < rod || !finite(si)) continue;
                if (Double.isNaN(atRail)) atRail = si;
                if (ti <= burnEnd) minBurn = Double.isNaN(minBurn) ? si : Math.min(minBurn, si);
            }
        }
        if (Double.isNaN(minBurn)) minBurn = atRail;

        double twr = Double.NaN;
        List<Double> tw = main.get(FlightDataType.TYPE_THRUST_WEIGHT_RATIO);
        if (t != null && tw != null && !Double.isNaN(liftoff)) {
            double end = !Double.isNaN(rod) ? rod : !Double.isNaN(burnout) ? burnout : t.get(t.size() - 1);
            twr = timeMean(t, tw, liftoff, end);
        }

        m.put("ok", true);
        m.put("abort", abort);
        m.put("apogee_m", num(d.getMaxAltitude()));
        m.put("max_velocity_ms", num(d.getMaxVelocity()));
        m.put("max_accel_ms2", num(d.getMaxAcceleration()));
        m.put("max_mach", num(d.getMaxMachNumber()));
        m.put("time_to_apogee_s", num(d.getTimeToApogee()));
        m.put("flight_time_s", num(d.getFlightTime()));
        m.put("ground_hit_ms", num(d.getGroundHitVelocity()));
        m.put("rail_exit_ms", num(d.getLaunchRodVelocity()));
        m.put("stability_rail_cal", num(atRail));
        m.put("stability_min_burn_cal", num(minBurn));
        m.put("burnout_time_s", num(burnout));
        m.put("ignition_time_s", num(firstEventTime(main, FlightEvent.Type.IGNITION)));
        m.put("liftoff_twr", num(twr));

        boolean timeCap = false;
        List<Object> branches = new ArrayList<>();
        for (int bi = 0; bi < d.getBranchCount(); bi++) {
            FlightDataBranch b = d.getBranch(bi);
            Map<String, Object> bm = new LinkedHashMap<>();
            bm.put("index", bi);
            bm.put("name", String.valueOf(b.getName()));
            Boolean hasRec = counter.recoveryByBranch.get(b);
            double dep = firstEventTime(b, FlightEvent.Type.RECOVERY_DEVICE_DEPLOYMENT);
            double ground = firstEventTime(b, FlightEvent.Type.GROUND_HIT);
            List<Double> bt = b.get(FlightDataType.TYPE_TIME);
            List<Double> vt = b.get(FlightDataType.TYPE_VELOCITY_TOTAL);
            List<Double> vz = b.get(FlightDataType.TYPE_VELOCITY_Z);
            // Every recovery device that opened on this branch (a drogue and a main both count):
            // the fastest opening and any opening during a burn are what matter for safety.
            List<Object> deployments = new ArrayList<>();
            double fastest = Double.NaN;
            boolean anyDuringBurn = false;
            for (FlightEvent e : b.getEvents()) {
                if (e.getType() != FlightEvent.Type.RECOVERY_DEVICE_DEPLOYMENT) continue;
                double te = e.getTime();
                double speed = interpolate(bt, vt, te);
                boolean burning = burningAt(b, te);
                Map<String, Object> dm = new LinkedHashMap<>();
                RocketComponent src = e.getSource();
                dm.put("device", src == null ? null : String.valueOf(src.getName()));
                dm.put("time_s", num(te));
                dm.put("speed_ms", num(speed));
                dm.put("during_burn", burning);
                deployments.add(dm);
                if (finite(speed) && (Double.isNaN(fastest) || speed > fastest)) fastest = speed;
                anyDuringBurn |= burning;
            }
            bm.put("has_recovery", hasRec);
            bm.put("deployed", !Double.isNaN(dep));
            bm.put("deploy_time_s", num(dep));
            bm.put("deploy_speed_ms", num(fastest));
            bm.put("deploy_during_burn", deployments.isEmpty() ? null : (Object) anyDuringBurn);
            bm.put("deployments", deployments);
            boolean landed = !Double.isNaN(ground);
            bm.put("landed", landed);
            bm.put("landing_time_s", num(ground));
            // The speeds at touchdown, not at the last sample: OpenRocket may keep simulating a branch
            // after it hit the ground (a rocket that lands while its motor burns), and then the last
            // sample is at rest.
            int hit = landed ? groundHitSample(bt, b.get(FlightDataType.TYPE_ALTITUDE), ground) : -1;
            bm.put("landing_vertical_ms", num(hit >= 0 && vz != null && hit < vz.size() ? -val(vz.get(hit)) : Double.NaN));
            bm.put("landing_total_ms", num(hit >= 0 && vt != null && hit < vt.size() ? val(vt.get(hit)) : Double.NaN));
            double last = bt == null || bt.isEmpty() ? Double.NaN : bt.get(bt.size() - 1);
            bm.put("last_time_s", num(last));
            // OpenRocket ends a branch on GROUND_HIT, on an abort or error, or when the simulated time
            // reaches max_sim_time_s (its last sample may then lie up to one step before the cap).
            boolean stoppedEarly = !Double.isNaN(firstEventTime(b, FlightEvent.Type.SIM_ABORT))
                    || !Double.isNaN(firstEventTime(b, FlightEvent.Type.EXCEPTION));
            if (!landed && !Double.isNaN(last) && !stoppedEarly && !stepCap) timeCap = true;
            branches.add(bm);
        }
        m.put("branches", branches);

        TreeSet<String> warns = new TreeSet<>();
        WarningSet ws = d.getWarningSet();
        if (ws != null) for (Object w : ws) warns.add(plain(String.valueOf(w)));
        m.put("warnings", new ArrayList<>(warns));
        m.put("steps", counter.steps[0]);
        m.put("hit_step_cap", stepCap);
        m.put("hit_time_cap", timeCap && !stepCap);
    }

    /** True when a motor mount of this branch had ignited at or before time t and not yet burnt out. */
    static boolean burningAt(FlightDataBranch b, double t) {
        Map<RocketComponent, Integer> state = new IdentityHashMap<>();
        for (FlightEvent e : b.getEvents()) {
            if (e.getTime() > t) continue;
            if (e.getType() == FlightEvent.Type.IGNITION) state.merge(e.getSource(), 1, Integer::sum);
            else if (e.getType() == FlightEvent.Type.BURNOUT) state.merge(e.getSource(), -1, Integer::sum);
        }
        for (int v : state.values()) if (v > 0) return true;
        return false;
    }

    /**
     * Index of the touchdown sample of a branch whose first GROUND_HIT event is at time ground:
     * the sample stored at that time (OpenRocket stores the step that reached the ground before it
     * fires the event); when no sample sits at the event time, the last sample before it that is
     * still above the ground, else the last sample before it. -1 when there is none.
     */
    static int groundHitSample(List<Double> t, List<Double> alt, double ground) {
        if (t == null || t.isEmpty() || Double.isNaN(ground)) return -1;
        int before = -1, above = -1;
        for (int i = 0; i < t.size(); i++) {
            Double ti = t.get(i);
            if (ti == null) continue;
            if (Math.abs(ti - ground) <= 1e-9) return i;
            if (ti > ground) break;
            before = i;
            if (alt != null && i < alt.size() && val(alt.get(i)) > 0) above = i;
        }
        return above >= 0 ? above : before;
    }

    static double firstEventTime(FlightDataBranch b, FlightEvent.Type type) {
        double best = Double.NaN;
        for (FlightEvent e : b.getEvents()) if (e.getType() == type && (Double.isNaN(best) || e.getTime() < best)) best = e.getTime();
        return best;
    }

    static double lastEventTime(FlightDataBranch b, FlightEvent.Type type) {
        double best = Double.NaN;
        for (FlightEvent e : b.getEvents()) if (e.getType() == type && (Double.isNaN(best) || e.getTime() > best)) best = e.getTime();
        return best;
    }

    /** Value of series y at time x by straight-line interpolation; the end value outside the samples. */
    static double interpolate(List<Double> xs, List<Double> ys, double x) {
        if (xs == null || ys == null) return Double.NaN;
        int n = Math.min(xs.size(), ys.size());
        if (n == 0) return Double.NaN;
        if (x <= xs.get(0)) return val(ys.get(0));
        for (int i = 1; i < n; i++) {
            double x1 = xs.get(i);
            if (x <= x1) {
                double x0 = xs.get(i - 1), y0 = val(ys.get(i - 1)), y1 = val(ys.get(i));
                if (x1 == x0) return y1;
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0);
            }
        }
        return val(ys.get(n - 1));
    }

    /** Time-weighted mean of y over [a, b] using the samples inside it (trapezoid rule); the sample value when only one lies inside. */
    static double timeMean(List<Double> xs, List<Double> ys, double a, double b) {
        int n = Math.min(xs.size(), ys.size());
        double area = 0, span = 0, single = Double.NaN;
        double px = Double.NaN, py = Double.NaN;
        for (int i = 0; i < n; i++) {
            double x = xs.get(i), y = val(ys.get(i));
            if (x < a || x > b || !finite(y)) continue;
            if (Double.isNaN(single)) single = y;
            if (!Double.isNaN(px)) { area += (x - px) * (y + py) / 2; span += x - px; }
            px = x;
            py = y;
        }
        return span > 0 ? area / span : single;
    }

    static double val(Double d) { return d == null ? Double.NaN : d; }

    static boolean finite(double d) { return !Double.isNaN(d) && !Double.isInfinite(d); }

    // ------------------------------------------------------------------ small helpers

    /** A finite number, or null (JSON has no NaN or infinity). */
    static Object num(Double d) {
        if (d == null || d.isNaN() || d.isInfinite()) return null;
        return d;
    }

    /**
     * OpenRocket's text as plain language: some of its messages are HTML ("<html>Motor burnout
     * without liftoff. <br>Use more ...</html>"). Line breaks become spaces, tags are removed,
     * the common entities are decoded and runs of white space become one space.
     */
    static String plain(String s) {
        if (s == null) return null;
        String t = s.replaceAll("(?i)<br\\s*/?>", " ").replaceAll("<[^<>]+>", "");
        t = t.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"").replace("&#39;", "'")
                .replace("&nbsp;", " ").replace("&amp;", "&");
        return t.replaceAll("\\s+", " ").trim();
    }

    static String describe(Throwable t) {
        String msg = t.getMessage();
        String name = t.getClass().getSimpleName();
        if (msg == null || msg.isEmpty()) return name;
        return name + ": " + msg;
    }

    /**
     * True when the exception was thrown by this helper's own code (a bug here), not by
     * OpenRocket while reading, building or flying a design.
     */
    static boolean isHelperBug(Throwable t) {
        if (t instanceof BadRequest) return true;
        // A wiring fault in OpenRocket's start-up (missing binding) or a full memory is a machine
        // problem, never a fault of the design that happened to trigger it.
        for (Throwable c = t; c != null; c = c.getCause() == c ? null : c.getCause()) {
            if (c instanceof VirtualMachineError && !(c instanceof StackOverflowError)) return true;
            if (c.getClass().getName().startsWith("com.google.inject.")) return true;
        }
        // Look past the Java library frames (a list index error raised inside java.util still
        // belongs to whoever called it) and decide by the first frame that is ours or OpenRocket's.
        for (StackTraceElement f : t.getStackTrace()) {
            String c = f.getClassName();
            if (c.startsWith("java.") || c.startsWith("javax.") || c.startsWith("jdk.") || c.startsWith("sun.")) continue;
            return c.equals("RocketSim") || c.startsWith("RocketSim$");
        }
        return false;
    }

    static final class BadRequest extends Exception {
        BadRequest(String m) { super(m); }
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

    // ------------------------------------------------------------------ JSON

    /** Minimal JSON reader and writer: objects, arrays, strings (all escapes), numbers, true/false/null. */
    static final class Json {
        private final String s;
        private int i;

        private Json(String s) { this.s = s; }

        static Object parse(String text) throws BadRequest {
            Json p = new Json(text);
            p.ws();
            Object v = p.value(0);
            p.ws();
            if (p.i != p.s.length()) throw new BadRequest("extra text after the JSON value at position " + p.i);
            return v;
        }

        private void ws() {
            while (i < s.length()) {
                char c = s.charAt(i);
                if (c == ' ' || c == '\t' || c == '\n' || c == '\r') i++; else break;
            }
        }

        private BadRequest err(String what) { return new BadRequest(what + " at position " + i); }

        private Object value(int depth) throws BadRequest {
            if (depth > 200) throw err("nested too deeply");
            if (i >= s.length()) throw err("unexpected end of text");
            char c = s.charAt(i);
            switch (c) {
                case '{': return object(depth);
                case '[': return array(depth);
                case '"': return string();
                case 't': return word("true", Boolean.TRUE);
                case 'f': return word("false", Boolean.FALSE);
                case 'n': return word("null", null);
                default:
                    if (c == '-' || (c >= '0' && c <= '9')) return number();
                    throw err("unexpected character '" + c + "'");
            }
        }

        private Object word(String w, Object v) throws BadRequest {
            if (!s.startsWith(w, i)) throw err("unknown word");
            i += w.length();
            return v;
        }

        private Map<String, Object> object(int depth) throws BadRequest {
            Map<String, Object> m = new LinkedHashMap<>();
            i++;
            ws();
            if (i < s.length() && s.charAt(i) == '}') { i++; return m; }
            while (true) {
                ws();
                if (i >= s.length() || s.charAt(i) != '"') throw err("expected a key");
                String k = string();
                ws();
                if (i >= s.length() || s.charAt(i) != ':') throw err("expected ':'");
                i++;
                ws();
                m.put(k, value(depth + 1));
                ws();
                if (i >= s.length()) throw err("unexpected end of text");
                char c = s.charAt(i++);
                if (c == '}') return m;
                if (c != ',') throw err("expected ',' or '}'");
            }
        }

        private List<Object> array(int depth) throws BadRequest {
            List<Object> a = new ArrayList<>();
            i++;
            ws();
            if (i < s.length() && s.charAt(i) == ']') { i++; return a; }
            while (true) {
                ws();
                a.add(value(depth + 1));
                ws();
                if (i >= s.length()) throw err("unexpected end of text");
                char c = s.charAt(i++);
                if (c == ']') return a;
                if (c != ',') throw err("expected ',' or ']'");
            }
        }

        private String string() throws BadRequest {
            StringBuilder b = new StringBuilder();
            i++;
            while (true) {
                if (i >= s.length()) throw err("unfinished string");
                char c = s.charAt(i++);
                if (c == '"') return b.toString();
                if (c < 0x20) throw err("control character inside a string");
                if (c != '\\') { b.append(c); continue; }
                if (i >= s.length()) throw err("unfinished escape");
                char e = s.charAt(i++);
                switch (e) {
                    case '"': b.append('"'); break;
                    case '\\': b.append('\\'); break;
                    case '/': b.append('/'); break;
                    case 'b': b.append('\b'); break;
                    case 'f': b.append('\f'); break;
                    case 'n': b.append('\n'); break;
                    case 'r': b.append('\r'); break;
                    case 't': b.append('\t'); break;
                    case 'u':
                        if (i + 4 > s.length()) throw err("short \\u escape");
                        int code = 0;
                        for (int k = 0; k < 4; k++) {
                            int h = Character.digit(s.charAt(i + k), 16);
                            if (h < 0) throw err("bad \\u escape");
                            code = code * 16 + h;
                        }
                        i += 4;
                        b.append((char) code); // surrogate pairs arrive as two escapes and join up here
                        break;
                    default: throw err("unknown escape \\" + e);
                }
            }
        }

        private Object number() throws BadRequest {
            int start = i;
            if (s.charAt(i) == '-') i++;
            if (i >= s.length()) throw err("bad number");
            if (s.charAt(i) == '0') i++;
            else if (Character.isDigit(s.charAt(i))) { while (i < s.length() && Character.isDigit(s.charAt(i))) i++; }
            else throw err("bad number");
            boolean integral = true;
            if (i < s.length() && s.charAt(i) == '.') {
                integral = false;
                i++;
                if (i >= s.length() || !Character.isDigit(s.charAt(i))) throw err("bad number");
                while (i < s.length() && Character.isDigit(s.charAt(i))) i++;
            }
            if (i < s.length() && (s.charAt(i) == 'e' || s.charAt(i) == 'E')) {
                integral = false;
                i++;
                if (i < s.length() && (s.charAt(i) == '+' || s.charAt(i) == '-')) i++;
                if (i >= s.length() || !Character.isDigit(s.charAt(i))) throw err("bad number");
                while (i < s.length() && Character.isDigit(s.charAt(i))) i++;
            }
            String t = s.substring(start, i);
            if (integral && t.length() <= 18) return Long.parseLong(t);
            return Double.parseDouble(t);
        }

        static String write(Object v) {
            StringBuilder b = new StringBuilder();
            write(b, v);
            return b.toString();
        }

        static void write(StringBuilder b, Object v) {
            if (v == null) { b.append("null"); return; }
            if (v instanceof Boolean) { b.append(((Boolean) v) ? "true" : "false"); return; }
            if (v instanceof Integer || v instanceof Long) { b.append(v.toString()); return; }
            if (v instanceof Number) {
                double d = ((Number) v).doubleValue();
                if (Double.isNaN(d) || Double.isInfinite(d)) b.append("null");
                else b.append(Double.toString(d));
                return;
            }
            if (v instanceof String) { str(b, (String) v); return; }
            if (v instanceof Map) {
                b.append('{');
                boolean first = true;
                for (Map.Entry<?, ?> e : ((Map<?, ?>) v).entrySet()) {
                    if (!first) b.append(',');
                    first = false;
                    str(b, String.valueOf(e.getKey()));
                    b.append(':');
                    write(b, e.getValue());
                }
                b.append('}');
                return;
            }
            if (v instanceof Collection) {
                b.append('[');
                boolean first = true;
                for (Object o : (Collection<?>) v) {
                    if (!first) b.append(',');
                    first = false;
                    write(b, o);
                }
                b.append(']');
                return;
            }
            str(b, String.valueOf(v));
        }

        /** Quoted string; control characters, quotes, backslashes and the line separators U+2028/2029 are escaped. */
        static void str(StringBuilder b, String s) {
            b.append('"');
            for (int k = 0; k < s.length(); k++) {
                char c = s.charAt(k);
                switch (c) {
                    case '"': b.append("\\\""); break;
                    case '\\': b.append("\\\\"); break;
                    case '\n': b.append("\\n"); break;
                    case '\r': b.append("\\r"); break;
                    case '\t': b.append("\\t"); break;
                    case '\b': b.append("\\b"); break;
                    case '\f': b.append("\\f"); break;
                    default:
                        if (c < 0x20 || c == 0x2028 || c == 0x2029 || Character.isSurrogate(c) && !validSurrogate(s, k)) {
                            b.append(String.format(Locale.ROOT, "\\u%04x", (int) c));
                        } else {
                            b.append(c);
                        }
                }
            }
            b.append('"');
        }

        /** A lone surrogate cannot be written as UTF-8; such characters are escaped instead. */
        static boolean validSurrogate(String s, int k) {
            char c = s.charAt(k);
            if (Character.isHighSurrogate(c)) return k + 1 < s.length() && Character.isLowSurrogate(s.charAt(k + 1));
            return k > 0 && Character.isHighSurrogate(s.charAt(k - 1));
        }
    }
}
