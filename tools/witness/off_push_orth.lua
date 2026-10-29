-- off_push_orth.lua -- witness W1 for proofs/hu-off.md (Lemma S, case M2: legal orthogonal push)
-- STATUS: written, NOT RUN (do not run on Ivan's laptop while he uses it; hand to a tester agent).
--
-- Harness pattern: src/test/testmove.lua (runs inside a started game, rebuilds the current
-- level with des.reset_level ... des.finalize_level, feeds keys with nh.pushkey + nh.doturn).
-- Coordinates: des.map is placed at absolute (1,0). Before des.finalize_level, des.* coords are
-- map-relative (xstart=1, ystart=0: src/src/mklev.c:922, src/src/sp_lev.c:6182). After
-- finalize, xstart=ystart=0 (src/src/mklev.c:1555), so obj.at() and u.ux/u.uy are absolute.
-- Expected: every check passes; any error() means the simulation lemma (or the harness) is wrong.

nh.parse_config("OPTIONS=number_pad:0");
nh.parse_config("OPTIONS=!timed_delay");
nh.parse_config("OPTIONS=!autopickup");
nh.debug_flags({ mongen = false, hunger = false });

local OX, OY = 1, 0;  -- absolute = map-relative + (OX, OY)

local function check(cond, msg)
   if (not cond) then
      error("W1 FAIL: " .. msg);
   end
end

-- absolute coordinates; valid after des.finalize_level()
local function boulder_at(ax, ay)
   local o = obj.at(ax, ay);
   while (o ~= nil and not o:isnull()) do
      if (o:totable().otyp_name == "boulder") then
         return true;
      end
      o = o:next(true);  -- nexthere chain
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

-- build a level; boulders/start are map-relative; heavy = give the cursed loadstone
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

-- hero (1,1), boulder (2,1), cells (3,1)..(5,1) free floor, (6,1) wall
build(CORRIDOR, { {2,1} }, {1,1}, true, true);
check(boulder_at(2 + OX, 1 + OY), "setup: boulder missing at (2,1)");

key("l");  -- east: s=(2,1) holds a boulder, r=(3,1) is free floor => push
check(hero_at(2, 1), "hero did not step into the vacated square (2,1)");
check(boulder_at(3 + OX, 1 + OY), "boulder not at r=(3,1) after the push");
check(not boulder_at(2 + OX, 1 + OY), "boulder still at s=(2,1)");

key("l");  -- second push: hero (3,1), boulder (4,1)
key("l");  -- third push:  hero (4,1), boulder (5,1)
check(hero_at(4, 1), "after 3 pushes hero should be at (4,1)");
check(boulder_at(5 + OX, 1 + OY), "after 3 pushes boulder should be at (5,1)");

key("l");  -- r=(6,1) is wall: push refused, heavy hero cannot squeeze => no move
check(hero_at(4, 1), "push into a wall moved the hero");
check(boulder_at(5 + OX, 1 + OY), "push into a wall moved the boulder");

nh.pline("W1 off_push_orth: all checks passed");
