import info.openrocket.core.database.motor.ThrustCurveMotorSet;
import info.openrocket.core.motor.ThrustCurveMotor;
import info.openrocket.core.startup.Application;

import java.io.PrintStream;
import java.util.ArrayList;
import java.util.List;

/**
 * Prints one JSON object per line for every thrust curve in OpenRocket's
 * built-in motor list, with the curve statistics OpenRocket itself computes
 * (burn time, average and peak thrust, total impulse, masses) and the raw
 * time/thrust points. Used by tools/build_motor_table.py; it boots OpenRocket
 * through the rocket_reward helper (RocketSim.boot) so the motor list is
 * exactly the one the reward flies with.
 *
 * Classpath: OpenRocket jar ; compiled RocketSim classes ; this class.
 */
public class MotorStats {
    public static void main(String[] args) throws Exception {
        PrintStream out = new PrintStream(new java.io.FileOutputStream(java.io.FileDescriptor.out), true, "UTF-8");
        RocketSim.boot();
        int n = 0;
        for (ThrustCurveMotorSet set : Application.getThrustCurveMotorSetDatabase().getMotorSets()) {
            for (ThrustCurveMotor mo : set.getMotors()) {
                StringBuilder b = new StringBuilder(512);
                b.append('{');
                str(b, "digest", mo.getDigest()); b.append(',');
                str(b, "manufacturer", mo.getManufacturer().getDisplayName()); b.append(',');
                str(b, "manufacturer_simple", mo.getManufacturer().getSimpleName()); b.append(',');
                str(b, "designation", mo.getDesignation()); b.append(',');
                str(b, "common_name", mo.getCommonName()); b.append(',');
                str(b, "type", String.valueOf(mo.getMotorType())); b.append(',');
                str(b, "case_info", mo.getCaseInfo()); b.append(',');
                str(b, "propellant_info", mo.getPropellantInfo()); b.append(',');
                str(b, "description", mo.getDescription()); b.append(',');
                b.append("\"available\":").append(mo.isAvailable()).append(',');
                num(b, "diameter_m", mo.getDiameter()); b.append(',');
                num(b, "length_m", mo.getLength()); b.append(',');
                num(b, "total_impulse_ns", mo.getTotalImpulseEstimate()); b.append(',');
                num(b, "average_thrust_n", mo.getAverageThrustEstimate()); b.append(',');
                num(b, "max_thrust_n", mo.getMaxThrustEstimate()); b.append(',');
                num(b, "burn_time_s", mo.getBurnTimeEstimate()); b.append(',');
                num(b, "curve_end_s", mo.getBurnTime()); b.append(',');
                num(b, "launch_mass_kg", mo.getLaunchMass()); b.append(',');
                num(b, "burnout_mass_kg", mo.getBurnoutMass()); b.append(',');
                arr(b, "delays_s", mo.getStandardDelays()); b.append(',');
                arr(b, "time_s", mo.getTimePoints()); b.append(',');
                arr(b, "thrust_n", mo.getThrustPoints());
                b.append('}');
                out.println(b);
                n++;
            }
        }
        out.flush();
        System.err.println("MotorStats: " + n + " motors");
        System.exit(0);
    }

    static void str(StringBuilder b, String k, String v) {
        b.append('"').append(k).append("\":");
        if (v == null) { b.append("null"); return; }
        b.append('"');
        for (int i = 0; i < v.length(); i++) {
            char c = v.charAt(i);
            if (c == '"' || c == '\\') b.append('\\').append(c);
            else if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
            else b.append(c);
        }
        b.append('"');
    }

    static void num(StringBuilder b, String k, double v) {
        b.append('"').append(k).append("\":");
        b.append(Double.isFinite(v) ? Double.toString(v) : "null");
    }

    static void arr(StringBuilder b, String k, double[] v) {
        b.append('"').append(k).append("\":[");
        if (v != null) {
            for (int i = 0; i < v.length; i++) {
                if (i > 0) b.append(',');
                b.append(Double.isFinite(v[i]) ? Double.toString(v[i]) : "null");
            }
        }
        b.append(']');
    }
}
