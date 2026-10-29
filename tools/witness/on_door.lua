-- on_door.lua -- witness for proofs/hu-on-lower.md, gadget G_D (one-way door, Lemma 3.3)
-- STATUS: written, NOT RUN. Conventions as in off_diag_push.lua (map-relative coords, OX/OY).
-- Test 1 (forbidden): from the q-side the door boulder cannot be moved or bypassed.
-- Test 2 (intended): from the e-side, push the door boulder into the pocket and pass to the q-side.

nh.parse_config("OPTIONS=number_pad:0");
nh.parse_config("OPTIONS=!timed_delay");
nh.parse_config("OPTIONS=!autopickup");
nh.debug_flags({ mongen = false, hunger = false });

local OX, OY = 1, 0;

local function check(cond, msg) if (not cond) then error("G_D FAIL: " .. msg); end end
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

-- e=(3,1), X=(4,1) door boulder, pocket P=(5,1), q=(4,2), (4,3), (4,4); approach (1,1),(2,1).
-- sentinel pit at (8,5).
local MAP = {
   "         ",
   " .....   ",   -- (1,1) (2,1) e=(3,1) X=(4,1) pocket=(5,1)
   "    .    ",   -- q=(4,2)
   "    .    ",
   "    .    ",
   "        .",
};

local function build(start)
   des.reset_level();
   des.level_flags("noflip", "sokoban", "noteleport");
   des.level_init({ style = "solidfill", fg = " ", lit = true });
   des.map({ x = OX, y = OY, map = table.concat(MAP, "\n") });
   des.object("boulder", 4, 1);                -- Kd on X
   des.trap("pit", 8, 5);                       -- sentinel
   des.teleport_region({ region = { start[1] + OX, start[2] + OY, start[1] + OX, start[2] + OY },
                         region_islev = true, dir = "both" });
   des.finalize_level();
   u.clear_inventory();
   u.giveobj(obj.new("cursed loadstone"));
   check(hero_at(start[1], start[2]), "hero not placed");
end

-- Test 1: from the q-side
build({4, 4});
key("k"); key("k");
check(hero_at(4, 2), "did not reach q");
key("k");                                  -- FORBIDDEN: push Kd north into stone
check(hero_at(4, 2) and boulder_at(4, 1), "door boulder moved from the q-side");
key("y");                                  -- FORBIDDEN: diagonal q->e, corners X(boulder),(3,2)(stone)
check(hero_at(4, 2), "diagonal q->e succeeded");
key("u");                                  -- FORBIDDEN: diagonal q->P, corners X(boulder),(5,2)(stone)
check(hero_at(4, 2), "diagonal q->pocket succeeded");

-- Test 2: from the e-side
build({1, 1});
key("l"); key("l");
check(hero_at(3, 1), "did not reach e");
key("l");                                  -- push Kd into the pocket
check(hero_at(4, 1) and boulder_at(5, 1), "door not opened");
key("j"); key("j");
check(hero_at(4, 3), "q-side not reached after opening");

nh.pline("on_door: all checks passed");
