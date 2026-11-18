# Spotlight

Every Sunday, Spotlight features up to ten challenges from the official pwn.college curriculum and ten from community dojos. Both modules share a history. A challenge can appear again once both modules have run out of new picks.

The [rotation workflow](./.github/workflows/rotate.yml) sets the schedule, the number of challenges per module, and whether to include course dojos.

The blacklist covers dojos that repeat content, copy challenges from other dojos, or have broken or unsolvable challenges. An entry can exclude an entire dojo, one module, or a single challenge. See [blacklist.yml](./blacklist.yml).

## Automatic updates

Rotation pushes the new picks with the `ROTATE_DEPLOY_KEY` deploy key. The push triggers [Update Dojo](./.github/workflows/update.yml), which uses the `UPDATE_CODE` secret from the dojo admin page. Either workflow can also be run manually from GitHub Actions.
