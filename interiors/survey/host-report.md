# Interior host survey and first blockout

Original city files are unchanged. Only D is built, to blockout stage, in Nova_City_interiors.blend.

## Confirmed inventory

Nova: 896 city-scene objects. Veyra: 1231 city-scene objects. Both have 110 tower glazing meshes. All shared Tower object bounding boxes match between files.

Podium base z=4 is not a universal walkable-ground height. Actual surfaces include terrain z=2, canal avenue z=4.5, promenade and district boulevards z=6, and civic paving z=8. Entry design must use local measurements.

## Host schedule

| Rooms | Host | Measured podium footprint | Status / reason |
|---|---|---|---|
| D / G | Tower 047 | 55.46 × 60.98 m | D selected and blocked out; G reserved at identical coordinates. Beside canal transport; room fits within both shells. |
| A / F | Tower 054 | 60.33 × 60.00 m | Candidate: broad square footprint suits the circular hall. Veyra Landmark 02 also overlaps and must be audited before selection. |
| C / H | Tower 061 | 59.17 × 52.92 m | Candidate: 346.48m glazing top and broader footprint than the tallest tower, suitable for five-story atrium. |
| B | Tower 049 | 58.36 × 47.68 m | Candidate: canal-side podium; two-entry indoor arcade fits along the long dimension. |
| J / K | Gateway towers candidate | Combined object spans 248 × 58 m | Not selected: disconnected tower components must be measured independently; combined bounds are not usable room area. |
| I | Cliff beside Waterfall 02 candidate | Pending sectional survey | Underground extension allowed by brief; cave depth, entrance and waterfall intersections must be verified. |

## D blockout

Host center: (-161.28067, -229.41808). Podium bounds: (-189.0091, -259.9104, 4) to (-133.5523, -198.9258, 16). Glazing bounds: (-181.5091, -252.4104, 16) to (-141.0523, -206.4258, 99.0345). Crown top: 103.0345.

Concourse z=6; gallery z=12; vault crown z=30; sealed upper ceiling underside z=32.6. Main camera eye z=7.7. Entry widths 6m, heights 4.5m. East access reaches the canal avenue at z=4.5; south access reaches terrain at z=2.

Hidden backup collection: `_BACKUP | Tower 047`. Shell parts retain their original names. New room collections include Shell, Architecture, Props, Foliage, Lighting and Collision. Foliage is intentionally empty at blockout stage.

See D-transit/qa-blockout.json for measured mesh and floor-grid checks. Whole-room gameplay QA and reference comparison are pending. The gallery currently uses a visible walkable ramp in place of detailed stairs.

The requested blockout checkpoint is pending review; no final detailing, Veyra interior work or engine export has been performed.