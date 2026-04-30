# Klipper Extra: attach_search
# Final Production Version

class AttachProbeSearch:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.dock_x = config.getfloat('dock_x')
        self.dock_y = config.getfloat('dock_y')
        self.search_dist = config.getfloat('search_dist', 50.0)
        self.search_step = config.getfloat('search_step', 1.0)
        self.search_speed = config.getfloat('search_speed', 5.0)
        self.slide_dist = config.getfloat('slide_dist', 50.0)
        self.attached_state = config.getint('attached_state', 0)
        # Settle parameters: extra distance to lower after contact, and dwell time
        self.settle_dist = config.getfloat('settle_dist', 0.5)
        self.settle_dwell = config.getfloat('settle_dwell', 1.0)  # seconds
        self.gcode.register_command("ATTACH_PROBE_SEARCH", self.cmd_ATTACH_PROBE_SEARCH)

    def cmd_ATTACH_PROBE_SEARCH(self, gcmd):
        probe = self.printer.lookup_object('probe', None)
        toolhead = self.printer.lookup_object('toolhead')
        kin = toolhead.get_kinematics()

        # 1. Homing Check
        cur_homed = toolhead.get_status(self.printer.get_reactor().monotonic())['homed_axes']
        if 'x' not in cur_homed or 'y' not in cur_homed:
            raise gcmd.error("X and Y must be homed first.")

        # 2. Initial Probe Check
        toolhead.wait_moves()
        if probe.mcu_probe.query_endstop(toolhead.get_last_move_time()) == self.attached_state:
            gcmd.respond_info("Probe already attached.")
            return

        # 3. Establish Fake Z Home (Z=search_dist)
        toolhead.wait_moves()
        cur_pos = toolhead.get_position()
        fake_pos = [cur_pos[0], cur_pos[1], self.search_dist, cur_pos[3]]
        kin.set_position(fake_pos, ['x', 'y', 'z'])
        toolhead.set_position(fake_pos)

        # 4. Move to Dock
        toolhead.move([self.dock_x, self.dock_y, self.search_dist, cur_pos[3]], 100.0)
        toolhead.wait_moves()

        # 5. Search Loop
        dist_moved = 0.0
        attached = False
        while dist_moved < self.search_dist:
            if self.printer.is_shutdown(): break
            pos = toolhead.get_position()
            pos[2] -= self.search_step
            if pos[2] < 0: break
            toolhead.move(pos, self.search_speed)
            toolhead.wait_moves()
            dist_moved += self.search_step
            if probe.mcu_probe.query_endstop(toolhead.get_last_move_time()) == self.attached_state:
                attached = True
                # Settle: lower extra distance to fully seat magnets
                if self.settle_dist > 0:
                    pos = toolhead.get_position()
                    pos[2] -= self.settle_dist
                    toolhead.move(pos, self.search_speed)
                    toolhead.wait_moves()
                # Dwell to let magnets settle
                if self.settle_dwell > 0:
                    reactor = self.printer.get_reactor()
                    reactor.pause(reactor.monotonic() + self.settle_dwell)
                break

        # 6. Finalize
        toolhead.wait_moves()
        if attached:
            # Slide out
            final_pos = toolhead.get_position()
            max_x = toolhead.get_status(self.printer.get_reactor().monotonic())['axis_maximum'][0]
            target_x = min(final_pos[0] + self.slide_dist, max_x)
            toolhead.move([target_x, final_pos[1], final_pos[2], final_pos[3]], 10.0)
            toolhead.wait_moves()
            gcmd.respond_info("Probe attached. Logic Z is currently fake.")
        else:
            raise gcmd.error("Probe not detected.")

def load_config(config):
    return AttachProbeSearch(config)
