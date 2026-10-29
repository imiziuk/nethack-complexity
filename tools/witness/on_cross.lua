-- on_cross.lua -- witness for proofs/hu-on-lower.md, gadget G_X (K-over-P crossover, Lemma 3.5)
-- STATUS: written, NOT RUN. Conventions as in off_diag_push.lua (map-relative coords, OX/OY).
-- NOTE: no "hardfloor" flag here: holes must be able to swallow the hero (assumption A1), and the
-- hole must not trigger impossible() on creation. Entering the hole is NOT tested (it ends the level).
-- Test 1 (forbidden + P pass): P walks the row through S; from S it cannot push the token north.
-- Test 2 (intended K pass): remove delta into the pocket, push token tau down into the hole (plug),
-- then walk S -> s1 -> s2.

nh.parse_config("OPTIONS=number_pad:0");
nh.parse_config("OPTIONS=!timed_delay");
nh.parse_config("OPTIONS=!autopickup");
nh.debug_flags({ mongen = false, hunger = false });

local OX, OY = 1, 0;

local function check(cond, msg) if (not cond) then error("G_X FAIL: " .. msg); end end
local function hero_at(mx, my) return u.ux == mx + OX and u.uy == my + OY; end
local function key(k) nh.pushkey(k); nh.doturn(true); end
local function boulder_at(mx, my)
   local o = obj.at(mx + OX, my + OY);
   while (o ~= nil and not o:isnull()) do
      if (o:totable().otyp_name == "boulder") then return true; end
      o = o:next(true);
   end
   return false;
end

-- §3.5 coordinates shifted by (+4,+3): n2=(4,1) delta, pocket=(5,1), K in (2,1),(3,1);
-- n1=(4,2) tau; P row y=3 from x=1..7, S=(4,3); s1=(4,4) hole; s2=(4,5), (4,6). Sentinel pit (10,7).
local MAP = {
   "           ",
   "  ....     ",   -- (2,1) (3,1) n2=(4,1) p=(5,1)
   "    .      ",   -- n1=(4,2)
   " .......   ",   -- P row, S=(4,3)
   "    .      ",   -- s1=(4,4), becomes a hole below
   "    .      ",   -- s2
   "    .      ",
   "          .",
};

local function build(start)
   des.reset_level();
   des.level_flags("noflip", "sokoban", "noteleport");
   des.level_init({ style = "solidfill", fg = " ", lit = true });
   des.map({ x = OX, y = OY, map = table.concat(MAP, "\n") });
   des.object("boulder", 4, 1);                -- delta on n2
   des.object("boulder", 4, 2);                -- tau on n1
   des.trap("hole", 4, 4);                      -- s1
   des.trap("pit", 10, 7);                      -- sentinel
   des.teleport_region({ region = { start[1] + OX, start[2] + OY, start[1] + OX, start[2] + OY },
                         region_islev = true, dir = "both" });
   des.finalize_level();
   u.clear_inventory();
   u.giveobj(obj.new("cursed loadstone"));
   check(hero_at(start[1], start[2]), "hero not placed");
end

-- Test 1: P pass and the forbidden north push
build({1, 3});
key("l"); key("l"); key("l");
check(hero_at(4, 3), "P did not reach S");
key("k");                                  -- FORBIDDEN: push tau north (delta behind it)
check(hero_at(4, 3) and boulder_at(4, 2) and boulder_at(4, 1), "token moved by a P visitor");
key("y");                                  -- FORBIDDEN: diagonal to (3,2): stone
check(hero_at(4, 3), "diagonal off the P row");
key("l"); key("l"); key("l");
check(hero_at(7, 3), "P could not cross");

-- Test 2: K pass
build({2, 1});
key("l");                                  -- to (3,1)
key("l");                                  -- push delta into the pocket
check(hero_at(4, 1) and boulder_at(5, 1), "delta not in pocket");
key("j");                                  -- push tau from n1 to S
check(hero_at(4, 2) and boulder_at(4, 3), "tau not on S");
key("j");                                  -- push tau into the hole: plugs it
check(hero_at(4, 3) and not boulder_at(4, 4), "hole not plugged");
key("j"); key("j");                        -- s1 (now floor), s2
check(hero_at(4, 5), "K did not pass the crossover");

nh.pline("on_cross: all checks passed");
