-- off_diag_push.lua -- witness W2 for proofs/hu-off.md (Lemma S, case M3: diagonal push refused)
-- STATUS: written, NOT RUN. Harness and coordinate conventions: see off_push_orth.lua header.
-- Source claim: src/src/hack.c:441-448 (Sokoban && dx && dy => "won't roll diagonally" =>
-- cannot_push), then could_move_onto_boulder() is false for the heavy hero (hack.c:139-163).
-- Control run (no "sokoban" flag) must show the same keystroke DOES push diagonally, so the
-- test is sensitive to the flag.

nh.parse_config("OPTIONS=number_pad:0");
nh.parse_config("OPTIONS=!timed_delay");
nh.parse_config("OPTIONS=!autopickup");
nh.debug_flags({ mongen = false, hunger = false });

local OX, OY = 1, 0;

local function check(cond, msg)
   if (not cond) then
      error("W2 FAIL: " .. msg);
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

local ROOM = [[
-------
|.....|
|.....|
|.....|
-------]];

-- hero (2,3); boulder (3,2) to the NE; beyond it (4,1) is free; both corners (2,2),(3,3) free
-- (so the corner rule of test_move does not fire and moverock() is reached).
build(ROOM, { {3,2} }, {2,3}, true, true);
key("u");  -- northeast
check(hero_at(2, 3), "Sokoban: hero moved on a diagonal push attempt");
check(boulder_at(3 + OX, 2 + OY), "Sokoban: boulder left (3,2)");
check(not boulder_at(4 + OX, 1 + OY), "Sokoban: boulder rolled diagonally to (4,1)");

-- control: same board without the sokoban flag => the diagonal push succeeds
build(ROOM, { {3,2} }, {2,3}, false, true);
key("u");
check(hero_at(3, 2), "control: hero did not follow the diagonal push");
check(boulder_at(4 + OX, 1 + OY), "control: boulder not pushed diagonally to (4,1)");

nh.pline("W2 off_diag_push: all checks passed");
