-- off_sentinel_pit.lua -- witness W5 for proofs/hu-off.md (invariant I4: the sokoban flag survives)
-- STATUS: written, NOT RUN. Harness and coordinate conventions: see off_push_orth.lua header.
-- Source claim: deltrap() calls maybe_finish_sokoban() for PIT/HOLE (src/src/trap.c:6546-6547),
-- which clears the flag only if no non-hero-made PIT or HOLE is left (7059-7097). A sealed,
-- unreachable sentinel PIT therefore keeps the flag after the only reachable pit is filled.
-- After filling, the corner-cutting test of W3(a) must still be refused.
-- Control: same board, pocket WITHOUT the sentinel pit => flag clears => the squeeze succeeds.

nh.parse_config("OPTIONS=number_pad:0");
nh.parse_config("OPTIONS=!timed_delay");
nh.parse_config("OPTIONS=!autopickup");
nh.debug_flags({ mongen = false, hunger = false });

local OX, OY = 1, 0;

local function check(cond, msg)
   if (not cond) then
      error("W5 FAIL: " .. msg);
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

-- Room cells (1..5, 1..2). Pocket cell (7,1) is enclosed by walls on all 8 sides and is at
-- Chebyshev distance >= 2 from every room cell, so the hero is never adjacent to it.
local MAP = [[
---------
|.....|.|
|.....|-|
---------]];

local function build(sentinel)
   des.reset_level();
   des.level_flags("noflip", "sokoban", "noteleport", "hardfloor", "solidify");
   des.level_init({ style = "solidfill", fg = " ", lit = true });
   des.map({ x = OX, y = OY, map = MAP });
   des.object("boulder", 2, 1);   -- will fill the reachable pit
   des.object("boulder", 5, 1);   -- corner boulder for the squeeze test
   des.object("boulder", 4, 2);   -- corner boulder for the squeeze test
   des.trap("pit", 3, 1);         -- the only reachable pit
   if (sentinel) then
      des.trap("pit", 7, 1);      -- sealed sentinel pit
   end
   des.teleport_region({ region = { 1 + OX, 1 + OY, 1 + OX, 1 + OY },
                         region_islev = true, dir = "both" });
   des.finalize_level();
   for _, v in pairs(nh.stairways()) do
      error("W5 HARNESS: unexpected stairway at " .. v.x .. "," .. v.y);
   end
   u.clear_inventory();
   u.giveobj(obj.new("cursed loadstone"));
   check(hero_at(1, 1), "hero not placed on (1,1)");
end

local function fill_and_walk()
   key("l");  -- push boulder (2,1) into the pit at (3,1): boulder used up, pit deleted
   check(hero_at(2, 1), "hero did not advance after the fill push");
   check(not boulder_at(3 + OX, 1 + OY), "boulder still visible on the pit square");
   key("l");  -- (3,1) is now plain floor
   check(hero_at(3, 1), "filled pit square not walkable");
   key("l");
   check(hero_at(4, 1), "hero did not reach (4,1)");
end

-- main run: sentinel present => flag stays => SE squeeze between (5,1) and (4,2) refused
build(true);
fill_and_walk();
key("n");  -- southeast to (5,2); corners (4,2) and (5,1) are boulders
check(hero_at(4, 1), "sokoban flag was cleared although the sentinel pit exists");

-- control: no sentinel => filling the only pit clears the flag => the same squeeze succeeds
build(false);
fill_and_walk();
key("n");
check(hero_at(5, 2), "control: flag did not clear after the last pit was filled");

nh.pline("W5 off_sentinel_pit: all checks passed");
