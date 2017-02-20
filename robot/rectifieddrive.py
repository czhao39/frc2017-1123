import logging

from networktables import NetworkTables

import subsystems
from inputs import navx


class RectifiedDrive:
    """
    This class implements rectified drive, which is essentially an enhanced version of arcade drive.
    It sets the motor outputs given a desired power and angular velocity using the NavX and a PID controller.
    """

    def __init__(self, max_angular_speed, period=0.03, tolerance=0.1, squared_inputs=True):
        self.sd = NetworkTables.getTable("SmartDashboard")

        # PID values for angular velocity
        self.kp = None
        self.ki = None
        self.kd = None
        # tolerance (as a fraction of max_angular_speed) for driving straight forward
        self.tolerance = abs(tolerance)

        self.max_angular_speed = abs(max_angular_speed)  # maximum angular velocity magnitude in degrees per second
        # squared inputs for angular velocity cause rectified drive to be less responsive at small deviations from straight forward
        self.squared_inputs = squared_inputs
        self.period = period  # period used for derivative calculation
        self.integral = 0  # total time elapsed used for integral calculation
        self.prev_error = 0  # previous error used for integral and derivative calculations

        self.logger = logging.getLogger('robot')

    def rectified_drive(self, power, angular_vel_frac):
        """
        Sets the motor outputs based on the given power and angular velocity (as a fraction of max_angular_speed).
        """
        self.kp = self.sd.getNumber("drive/kp")
        self.ki = self.sd.getNumber("drive/ki")
        self.kd = self.sd.getNumber("drive/kd")
        self.tolerance = abs(self.sd.getNumber("drive/ktolerance"))

        if power < 0.02:  # reset integral if close to 0
            self.integral = 0
        if abs(angular_vel_frac) < self.tolerance:
            angular_vel_frac = 0  # drive straight forward
        elif self.squared_inputs:
            angular_vel_frac = angular_vel_frac ** 2 * angular_vel_frac / abs(angular_vel_frac)

        angular_vel = angular_vel_frac * self.max_angular_speed
        actual = navx.ahrs.getRate()
        self.sd.putNumber("drive/setpoint", angular_vel)
        self.sd.putNumber("drive/actual", actual)

        error = actual - angular_vel
        output = self.calc_pid(error)
        left_output = power + output
        if abs(left_output) > 1.0:  # normalize if magnitude greater than 1
            left_output /= abs(left_output)
        right_output = power - output
        if abs(right_output) > 1.0:  # normalize if magnitude greater than 1
            right_output /= abs(right_output)
        subsystems.motors.robot_drive.setLeftRightMotorOutputs(left_output, right_output)

    def calc_pid(self, error):
        # self.logger.info("RectifiedDrive error {}".format(error))
        e_deriv = (error - self.prev_error) / self.period
        self.integral += (error + self.prev_error) / 2 * self.period
        self.prev_error = error
        return self.kp * error + self.kd * e_deriv + self.ki * self.integral
