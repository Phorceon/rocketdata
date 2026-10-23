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
/** Batch runner: stdin lines "path\tsimName\tseed\treps"; stdout one JSON line per run. */
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
  static String q(String s){ return "\"" + s.replace("\\","\\\\").replace("\"","\\\"") + "\""; }
  static String num(double d){ return (Double.isNaN(d)||Double.isInfinite(d)) ? "null" : Double.toString(d); }
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
          OpenRocketDocument doc = new GeneralRocketLoader(new File(path)).load();
          Simulation sim=null; List<String> names=new ArrayList<>();
          for (Simulation s: doc.getSimulations()) { names.add(s.getName()); if (s.getName().equals(name)) sim=s; }
          if (sim==null) throw new RuntimeException("simulation not found; available: "+names);
          reseed(sim.getOptions(), seed);
          sim.simulate();
          FlightData d = sim.getSimulatedData();
          sb.append(",\"apogee_m\":"+num(d.getMaxAltitude())+",\"max_velocity_ms\":"+num(d.getMaxVelocity())
            +",\"max_accel_ms2\":"+num(d.getMaxAcceleration())+",\"max_mach\":"+num(d.getMaxMachNumber())
            +",\"time_to_apogee_s\":"+num(d.getTimeToApogee())+",\"flight_time_s\":"+num(d.getFlightTime())
            +",\"ground_hit_ms\":"+num(d.getGroundHitVelocity())+",\"deployment_velocity_ms\":"+num(d.getDeploymentVelocity())
            +",\"wind_ms\":"+num(sim.getOptions().getWindSpeedAverage()));
          sb.append(",\"events\":[");
          boolean first=true;
          for (int b=0;b<d.getBranchCount();b++) for (FlightEvent e: d.getBranch(b).getEvents()) {
            if(!first) sb.append(","); first=false;
            sb.append("{\"branch\":"+b+",\"type\":"+q(e.getType().name())+",\"t\":"+num(e.getTime())+"}");
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
