import info.openrocket.core.startup.Application;
import info.openrocket.core.plugin.PluginModule;
import info.openrocket.swing.startup.GuiModule;
import info.openrocket.core.file.GeneralRocketLoader;
import info.openrocket.core.document.*;
import info.openrocket.core.simulation.*;
import info.openrocket.core.models.wind.*;
import com.google.inject.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;
/** Batch runner: stdin lines "path\tsimName\tseed\treps"; stdout one JSON line per run.
 *  Events carry their data payload (e.g. SIM_ABORT reason strings) as "data";
 *  .ork load warnings (missing motors, unknown elements) as "load_warnings". */
public class OrBatch {
  public static void boot() throws Exception {
    installDet();
    GuiModule gui = new GuiModule();
    Application.setInjector(Guice.createInjector(gui, new PluginModule()));
    Application.getPreferences();
    gui.startLoader();
    for (String f : new String[]{"presetLoader","motorLoader"}) {
      Field fl = gui.getClass().getDeclaredField(f); fl.setAccessible(true);
      Object o = fl.get(gui); o.getClass().getMethod("blockUntilLoaded").invoke(o);
    }
  }
  /** OpenRocket gives components that have no stored id a UUID.randomUUID(); those UUIDs key the
   *  FlightConfiguration motor HashMap, so motor iteration order (and the results of multi-motor /
   *  multi-stage sims) changes run to run. We install a deterministic SecureRandom provider before
   *  anything touches UUID, and reset its stream before every document load. */
  public static final class DetSpi extends java.security.SecureRandomSpi {
    static Random r = new Random(0);
    static synchronized void reset(long s){ r = new Random(s); }
    protected void engineSetSeed(byte[] seed) {}
    protected void engineNextBytes(byte[] b) { synchronized (DetSpi.class) { r.nextBytes(b); } }
    protected byte[] engineGenerateSeed(int n) { byte[] b=new byte[n]; engineNextBytes(b); return b; }
  }
  static final class DetProv extends java.security.Provider {
    DetProv(){ super("DetPRNG","1.0","deterministic PRNG for reproducible OpenRocket loads"); put("SecureRandom.DetPRNG", DetSpi.class.getName()); }
  }
  public static void installDet(){ java.security.Security.insertProviderAt(new DetProv(), 1); }
  public static void seedUUID(long seed){ DetSpi.reset(seed); }
  static PinkNoiseWindModel copy(PinkNoiseWindModel o, int seed){
    PinkNoiseWindModel m = new PinkNoiseWindModel(seed);
    m.setAverage(o.getAverage()); m.setStandardDeviation(o.getStandardDeviation()); m.setDirection(o.getDirection());
    return m;
  }
  /** SimulationOptions builds its wind models with a random seed at construction;
   *  setRandomSeed() does not reseed them. Rebuild them from the given seed. */
  public static void reseed(SimulationOptions opts, int seed) throws Exception {
    opts.setRandomSeed(seed);
    Field f = SimulationOptions.class.getDeclaredField("averageWindModel"); f.setAccessible(true);
    f.set(opts, copy((PinkNoiseWindModel) f.get(opts), seed));
    List<MultiLevelPinkNoiseWindModel.LevelWindModel> lv = opts.getMultiLevelWindModel().getLevels();
    Field mf = MultiLevelPinkNoiseWindModel.LevelWindModel.class.getDeclaredField("model"); mf.setAccessible(true);
    for (int i=0;i<lv.size();i++) mf.set(lv.get(i), copy((PinkNoiseWindModel) mf.get(lv.get(i)), seed + 7919*(i+1)));
  }
  /** JSON-string with every control character escaped: the strings come from .ork files the
   *  model generated, so unescaped newlines would split the one-JSON-line-per-run output. */
  static String q(String s) {
    StringBuilder sb = new StringBuilder("\"");
    for (int i = 0; i < s.length(); i++) {
      char c = s.charAt(i);
      switch (c) {
        case '"': sb.append("\\\""); break;
        case '\\': sb.append("\\\\"); break;
        case '\b': sb.append("\\b"); break;
        case '\f': sb.append("\\f"); break;
        case '\n': sb.append("\\n"); break;
        case '\r': sb.append("\\r"); break;
        case '\t': sb.append("\\t"); break;
        default:
          if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
          else sb.append(c);
      }
    }
    return sb.append('"').toString();
  }
  static String num(double d){ return (Double.isNaN(d)||Double.isInfinite(d)) ? "null" : Double.toString(d); }
  /** Safety numbers for scripts/reward.py: stability (cal) at rail exit and its minimum from rail exit
   *  to the last burnout (main branch), and per branch: name, recovery deployed, ground hit, and the
   *  vertical speed at the last sample (the touchdown speed). */
  static void safety(StringBuilder sb, FlightData d) {
    FlightDataBranch m = d.getBranch(0);
    List<Double> t = m.get(FlightDataType.TYPE_TIME), s = m.get(FlightDataType.TYPE_STABILITY);
    double rod = Double.NaN, burn = Double.NaN;
    for (FlightEvent e : m.getEvents()) {
      if (e.getType() == FlightEvent.Type.LAUNCHROD && Double.isNaN(rod)) rod = e.getTime();
      if (e.getType() == FlightEvent.Type.BURNOUT) burn = e.getTime();
    }
    double atRail = Double.NaN, minBurn = Double.NaN;
    if (t != null && s != null && !Double.isNaN(rod)) {
      for (int i = 0; i < Math.min(t.size(), s.size()); i++) {
        double ti = t.get(i), si = s.get(i);
        if (ti < rod || Double.isNaN(si) || Double.isInfinite(si)) continue;
        if (Double.isNaN(atRail)) atRail = si;
        if (!Double.isNaN(burn) && ti <= burn) minBurn = Double.isNaN(minBurn) ? si : Math.min(minBurn, si);
      }
    }
    if (Double.isNaN(minBurn)) minBurn = atRail;
    sb.append(",\"stability_rail_cal\":"+num(atRail)+",\"stability_min_burn_cal\":"+num(minBurn));
    sb.append(",\"branches\":[");
    for (int b = 0; b < d.getBranchCount(); b++) {
      FlightDataBranch br = d.getBranch(b);
      boolean dep = false, ground = false;
      for (FlightEvent e : br.getEvents()) {
        dep |= e.getType() == FlightEvent.Type.RECOVERY_DEVICE_DEPLOYMENT;
        ground |= e.getType() == FlightEvent.Type.GROUND_HIT;
      }
      List<Double> vz = br.get(FlightDataType.TYPE_VELOCITY_Z);
      double land = (vz == null || vz.isEmpty()) ? Double.NaN : Math.abs(vz.get(vz.size() - 1));
      sb.append((b > 0 ? "," : "")+"{\"name\":"+q(String.valueOf(br.getName()))+",\"deployed\":"+dep
        +",\"ground\":"+ground+",\"landing_ms\":"+num(land)+"}");
    }
    sb.append("]");
  }
  /** Every part as OpenRocket resolved it, for the fit checks in scripts/reward.py: absolute position of
   *  its fore end (x0, from the nose tip), length, radii, and for fin sets count, rotation and thickness. */
  static void geometry(StringBuilder sb, info.openrocket.core.rocketcomponent.Rocket rocket) {
    List<info.openrocket.core.rocketcomponent.RocketComponent> all = new ArrayList<>();
    Iterator<info.openrocket.core.rocketcomponent.RocketComponent> it = rocket.iterator(false);
    while (it.hasNext()) all.add(it.next());
    sb.append(",\"parts\":[");
    for (int i = 0; i < all.size(); i++) {
      info.openrocket.core.rocketcomponent.RocketComponent c = all.get(i);
      double x0 = Double.NaN;
      try { for (info.openrocket.core.util.Coordinate k : c.getComponentLocations()) x0 = Double.isNaN(x0) ? k.x : Math.min(x0, k.x); }
      catch (Throwable t) {}
      sb.append((i > 0 ? "," : "") + "{\"i\":" + i + ",\"parent\":" + all.indexOf(c.getParent()) + ",\"type\":" + q(c.getClass().getSimpleName())
        + ",\"name\":" + q(String.valueOf(c.getName())) + ",\"x0\":" + num(x0) + ",\"len\":" + num(c.getLength())
        + ",\"n\":" + c.getInstanceCount());
      if (c instanceof info.openrocket.core.rocketcomponent.SymmetricComponent) {
        info.openrocket.core.rocketcomponent.SymmetricComponent s = (info.openrocket.core.rocketcomponent.SymmetricComponent) c;
        sb.append(",\"r_fore\":" + num(s.getForeRadius()) + ",\"r_aft\":" + num(s.getAftRadius())
          + ",\"wall\":" + num(s.isFilled() ? -1 : s.getThickness())
          + ",\"r_fore_auto\":" + s.isForeRadiusAutomatic() + ",\"r_aft_auto\":" + s.isAftRadiusAutomatic());
      }
      if (c instanceof info.openrocket.core.rocketcomponent.RingComponent) {
        info.openrocket.core.rocketcomponent.RingComponent r = (info.openrocket.core.rocketcomponent.RingComponent) c;
        sb.append(",\"r_out\":" + num(r.getOuterRadius()) + ",\"r_in\":" + num(r.getInnerRadius()) + ",\"r_pos\":" + num(r.getRadialPosition()));
      }
      if (c instanceof info.openrocket.core.rocketcomponent.MassObject) {
        info.openrocket.core.rocketcomponent.MassObject m = (info.openrocket.core.rocketcomponent.MassObject) c;
        sb.append(",\"r_out\":" + num(m.getRadius()) + ",\"r_pos\":" + num(m.getRadialPosition()));
      }
      if (c instanceof info.openrocket.core.rocketcomponent.MotorMount && ((info.openrocket.core.rocketcomponent.MotorMount) c).isMotorMount()) {
        info.openrocket.core.rocketcomponent.MotorMount mm = (info.openrocket.core.rocketcomponent.MotorMount) c;
        info.openrocket.core.motor.Motor mo = null;
        // The editor's selected configuration need not be the one a simulation flies.
        // Diameter fit must hold for every configured motor; report the widest.
        for (info.openrocket.core.motor.MotorConfiguration mc : mm.getMotorConfigurationSet()) {
          info.openrocket.core.motor.Motor candidate = mc.getMotor();
          if (candidate != null && (mo == null || candidate.getDiameter() > mo.getDiameter())) mo = candidate;
        }
        if (mo != null) sb.append(",\"motor_d\":" + num(mo.getDiameter()) + ",\"motor_len\":" + num(mo.getLength())
          + ",\"overhang\":" + num(mm.getMotorOverhang()));
      }
      if (c instanceof info.openrocket.core.rocketcomponent.FinSet) {
        info.openrocket.core.rocketcomponent.FinSet f = (info.openrocket.core.rocketcomponent.FinSet) c;
        sb.append(",\"fins\":" + f.getFinCount() + ",\"rot\":" + num(Math.toDegrees(f.getBaseRotation())) + ",\"span\":" + num(f.getSpan())
          + ",\"thick\":" + num(f.getThickness()));
      }
      sb.append("}");
    }
    sb.append("]");
  }
  public static void main(String[] a) throws Exception {
    PrintStream out = new PrintStream(new FileOutputStream(FileDescriptor.out), true, "UTF-8");
    System.setOut(new PrintStream(OutputStream.nullOutputStream()));
    boot();
    BufferedReader in = new BufferedReader(new InputStreamReader(System.in, "UTF-8"));
    String line;
    while ((line = in.readLine()) != null) {
      if (line.isBlank()) continue;
      String[] p = line.split("\t");
      String path=p[0], name=p[1]; int seed=Integer.parseInt(p[2]); int reps=Integer.parseInt(p[3]); long useed = p.length>4 ? Long.parseLong(p[4]) : 42L;
      for (int r=0;r<reps;r++){
        StringBuilder sb = new StringBuilder("{\"file\":"+q(path)+",\"sim\":"+q(name)+",\"seed\":"+seed+",\"rep\":"+r+",\"uuid_seed\":"+useed);
        try {
          seedUUID(useed);
          GeneralRocketLoader loader = new GeneralRocketLoader(new File(path));
          OpenRocketDocument doc = loader.load();
          Simulation sim=null; List<String> names=new ArrayList<>();
          for (Simulation s: doc.getSimulations()) { names.add(s.getName()); if (s.getName().equals(name)) sim=s; }
          if (name.equals("__geometry__")) { geometry(sb, doc.getRocket()); sb.append("}"); out.println(sb); continue; }
          if (sim==null) throw new RuntimeException("simulation not found; available: "+names);
          reseed(sim.getOptions(), seed);
          sim.simulate();
          FlightData d = sim.getSimulatedData();
          sb.append(",\"apogee_m\":"+num(d.getMaxAltitude())+",\"max_velocity_ms\":"+num(d.getMaxVelocity())
            +",\"max_accel_ms2\":"+num(d.getMaxAcceleration())+",\"max_mach\":"+num(d.getMaxMachNumber())
            +",\"time_to_apogee_s\":"+num(d.getTimeToApogee())+",\"flight_time_s\":"+num(d.getFlightTime())
            +",\"ground_hit_ms\":"+num(d.getGroundHitVelocity())+",\"deployment_velocity_ms\":"+num(d.getDeploymentVelocity())
            +",\"wind_ms\":"+num(sim.getOptions().getWindSpeedAverage()));
          if (!loader.getWarnings().isEmpty()) {
            StringBuilder wl=new StringBuilder(); boolean wfirst=true;
            for (Object w : loader.getWarnings()) { if(!wfirst) wl.append(","); wfirst=false; wl.append(q(String.valueOf(w))); }
            sb.append(",\"load_warnings\":["+wl+"]");
          }
          sb.append(",\"rail_exit_ms\":"+num(d.getLaunchRodVelocity()));
          safety(sb, d);
          sb.append(",\"events\":[");
          boolean first=true;
          for (int b=0;b<d.getBranchCount();b++) for (FlightEvent e: d.getBranch(b).getEvents()) {
            if(!first) sb.append(","); first=false;
            sb.append("{\"branch\":"+b+",\"type\":"+q(e.getType().name())+",\"t\":"+num(e.getTime()));
            Object edata = e.getData();
            if (edata != null) sb.append(",\"data\":"+q(String.valueOf(edata)));
            sb.append("}");
          }
          sb.append("]}");
        } catch (Throwable t) {
          sb.append(",\"error\":"+q(t.getClass().getSimpleName()+": "+String.valueOf(t.getMessage()))+"}");
        }
        out.println(sb);
      }
    }
    System.exit(0);
  }
}
