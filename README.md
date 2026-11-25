# Spotlight

Spotlight features up to ten challenges from the official curriculum and ten from community dojos each week. [Play Spotlight on pwn.college](https://pwn.college/spotlight~072ac3dc/)

The Official and Community modules share a history. Challenges can return once both pools run out of new picks.

## Configuration

| Repository variable | Controls |
| --- | --- |
| `ALLOW_COURSE_DOJOS` | Whether course dojos are eligible |
| `AUTO_PRUNE_LEGACY_AWARDS` | Set to `true` to prune after a successful rotation update |
| `COMMUNITY_COUNT` | Number of community picks |
| `OFFICIAL_COUNT` | Number of official picks |

Use [blacklist.yml](./blacklist.yml) to exclude duplicate, broken, or unsolvable content by dojo, module, or challenge.

## Workflows

1. [Rotate Challenges](./.github/workflows/rotate.yml) selects the lineup on Sundays at 6:21 a.m. Pacific.
2. [Update Dojo](./.github/workflows/update.yml) publishes the rotation to pwn.college.
3. [Prune Legacy Awards](./.github/workflows/prune.yml) marks outdated completion awards stale.
