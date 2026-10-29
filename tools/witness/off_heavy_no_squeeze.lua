-- off_heavy_no_squeeze.lua -- witness W4 for proofs/hu-off.md (invariant I3: heavy hero never
-- steps onto a boulder square)
-- STATUS: written, NOT RUN. Harness and coordinate conventions: see off_push_orth.lua header.
-- Source claim: cannot_push() (src/src/hack.c:262-312) and the m-prefix branch (386-410) move the
-- hero onto the boulder only if could_move_onto_boulder() (145-163); for an unpolymorphed,
-- unmounted hero that is squeezeablylightinvent() = (!invent || inv_weight() <= -850)
-- (139-140, include/weight.h:24). Cursed loadstone = 500 (include/objects.h:1600) and
-- weight_cap() <= 1000 (hack.c:4325-4330) => inv_weight() >= -500 > -850.
-- Control: the same push with an EMPTY inventory squeezes onto the boulder square.

nh.parse_config("OPTIONS=number_pad:0");
nh.parse_config("OPTIONS=!timed_delay");
nh.parse_config("OPTIONS=!autopickup");
nh.debug_flags({ mongen = false, hunger = false });

local OX, OY = 1, 0;

local function check(cond, msg)
   if (not cond) then
      error("W4 FAIL: " .. msg);
   end
end

local function boulder_at(ax, ay)
   local o = obj.at(ax, ay);
   while (o ~= nil and not o:isnull()) do
      if (o:totable().otyp_name == "boulder") then
         return true;
      end
      o = o:next(true);
   end
   return false;
end

local function hero_at(mx, my)
   return u.ux == mx + OX and u.uy == my + OY;
end

local function key(k)
   nh.pushkey(k);
   nh.doturn(true);
end

local function build_once(map, boulders, start, soko, heavy)
   des.reset_level();
   if (soko) then
      des.level_flags("noflip", "sokoban", "noteleport", "hardfloor", "solidify");
   else
      des.level_flags("noflip", "noteleport", "hardfloor", "solidify");
   end
   des.level_init({ style = "solidfill", fg = " ", lit = true });
   des.map({ x = OX, y = OY, map = map });
   for _, b in ipairs(boulders) do
      des.object("boulder", b[1], b[2]);
   end
   des.teleport_region({ region = { start[1] + OX, start[2] + OY, start[1] + OX, start[2] + OY },
                         region_islev = true, dir = "both" });
   des.finalize_level();
   for _, v in pairs(nh.stairways()) do
      des.terrain(v.x, v.y, ".");  -- DL1 branch stair from finalize (review-2 N2), as in src/test/testmove.lua
   end
   u.clear_inventory();
   if (heavy) then
      u.giveobj(obj.new("cursed loadstone"));
   end
   return hero_at(start[1], start[2]);
end

-- harness retry: finalize places the DL1 branch stair at random; if it lands on the 1-cell start
-- region the hero is not placed ("Couldn't place lregion"). Setup randomness only, not gadget behaviour.
local function build(map, boulders, start, soko, heavy)
   for attempt = 1, 10 do
      if (build_once(map, boulders, start, soko, heavy)) then return; end
   end
   check(false, "hero not placed on the start square after 10 builds");
end

local CORRIDOR = [[
-------
|.....|
-------]];

-- heavy hero (4,1), boulder (5,1) against the wall (6,1)
build(CORRIDOR, { {5,1} }, {4,1}, true, true);
key("l");    -- push fails (wall beyond) => cannot_push => no squeeze
check(hero_at(4, 1), "heavy hero stepped onto a blocked boulder (plain move)");
key("ml");   -- m-prefix: never pushes; squeezes only if light
check(hero_at(4, 1), "heavy hero stepped onto a boulder with the m prefix");
check(boulder_at(5 + OX, 1 + OY), "boulder moved");
key("L");    -- shift-run east: run>=2 refuses boulders (hack.c:1216-1222); run==1 pushes and fails
check(hero_at(4, 1), "heavy hero passed a boulder while running");

-- control: empty inventory => squeeze succeeds (shows the test is sensitive to the weight)
build(CORRIDOR, { {5,1} }, {4,1}, true, false);
key("l");
check(hero_at(5, 1), "control: light hero did not squeeze onto the boulder square");
check(boulder_at(5 + OX, 1 + OY), "control: boulder should not move when squeezed past");

nh.pline("W4 off_heavy_no_squeeze: all checks passed");
