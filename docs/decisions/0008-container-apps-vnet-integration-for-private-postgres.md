# ADR 0008: VNet-integrate Container Apps to reach private Postgres

## Status
Accepted

## Context
Postgres (`pg-tad4471`) was created with **private access (VNet
Integration)** per the original plan's D3.4 — its only DNS name
(`pg-tad4471.postgres.database.azure.com`) resolves exclusively inside
the VNet it was delegated into (`rg-tad-manual-vnet`), via a linked
private DNS zone. Public network access is disabled entirely.

The first Container Apps environment (`cae-tad`) was created **without**
VNet integration, because the portal's simplified Container App creation
wizard defaults every new environment to **Express mode**, which has no
VNet option at all in that flow. `ca-tad-api` could build and start
successfully, but every request to Postgres failed with
`socket.gaierror: [Errno -2] Name or service not known` — from outside
the VNet, that FQDN simply doesn't exist.

A second, related problem surfaced independently: Express-mode
environments also reject **environment-level or user-assigned managed
identities** outright (`ExpressEnvironmentManagedIdentityNotSupported`),
which blocked the registry-pull identity needed to avoid the ACR admin
user. Both problems trace back to the same root cause — Express is a
newer, more restrictive environment type that the current portal UI
creates by default, with no visible toggle to opt out of it.

## Decision
Recreate the Container Apps environment with explicit
`--environment-mode WorkloadProfiles` and `--infrastructure-subnet-resource-id`
pointing at a **new, dedicated subnet** in the same VNet as Postgres.

Concretely:
- Expanded `rg-tad-manual-vnet`'s address space from a single `/24` to
  add a second `/23` block, since Container Apps VNet integration with
  Workload Profiles requires a subnet of at least `/23` — the existing
  `/24` was already fully consumed by Postgres's own delegated subnet.
- Created a new subnet (`containerapps`, `10.1.0.0/23`) delegated to
  `Microsoft.App/environments`.
- Deleted the old Express environment (`cae-tad`) and both Container Apps
  in it, then recreated the environment (`cae-tad-vnet`) and both apps
  fresh, since apps cannot be moved between environments and Azure for
  Students allows only **one Container Apps environment per region**
  (`MaxNumberOfRegionalEnvironmentsInSubExceeded`) — the old one had to
  be fully gone before the new one could be created.

## Alternatives considered
- **Give Postgres public access instead**, restricted by firewall rule to
  Container Apps' outbound IPs. Rejected: loses the private-networking
  learning goal the plan explicitly wanted from D3.4, and Container Apps'
  outbound IP list is large and not guaranteed stable, making a tight
  firewall rule impractical anyway.
- **Stay on Express, drop the managed-identity requirement, use the ACR
  admin user instead.** Rejected outright — directly contradicts D3.3's
  core goal (managed identity, zero secrets for registry auth), and
  Express still couldn't reach private Postgres regardless of identity
  model, so it wouldn't have solved the actual blocking problem.

## Consequences
- Every future Container App in this project must be created in
  `cae-tad-vnet`, never a fresh Express environment — the one-per-region
  quota means there is no "just spin up another environment" fallback if
  this one is deleted again.
- The VNet now has two subnets with two different delegations
  (`Microsoft.DBforPostgreSQL/flexibleServers` on `default`,
  `Microsoft.App/environments` on `containerapps`) sharing one address
  space — any future resource needing VNet placement (e.g. AKS in Phase
  6) needs its own further subnet, planned against the addresses already
  consumed here.
- Confirms and extends ADR 0007's general lesson about opaque portal
  defaults on this subscription: the *simplified* Container App creation
  wizard silently picks a more restrictive environment type than the
  CLI's own default, with no portal-visible way to override it. The CLI
  (`--environment-mode WorkloadProfiles`) was the only way to get the
  environment type this project actually needs — a portal-vs-CLI parity
  gap worth remembering for later phases (AKS is CLI/Terraform-only
  anyway, per the plan, so this class of gap won't recur there).

## Addendum: two more real bugs found while debugging this

Getting the API to actually query Postgres successfully surfaced two
further, unrelated mistakes worth recording since they cost real time:

1. **A password containing `@` broke connection-string parsing.** The
   `@` is the reserved delimiter between credentials and host in a
   standard URL; `postgresql+asyncpg://user:pass@word@host/db` parses
   the host as `word@host`, not `host`. Fixed by resetting the password
   to avoid URL-reserved characters (`@ : / % #` and spaces) entirely,
   rather than URL-encoding it — simpler and removes the whole class of
   bug for any future connection string built from the same credential.
2. **The deployed image never included `alembic.ini` or `migrations/`.**
   The API's Dockerfile only copied `src/` and `schemas/`; migrations had
   only ever been run against the local Compose Postgres. The first
   `alembic upgrade head` inside the deployed container failed with "No
   'script_location' key found" until the Dockerfile was fixed to copy
   both paths in.

Neither is Azure-specific, but both were only caught here because this
was the first time the app ran against infrastructure it didn't build
itself against (Compose's Postgres has an unrestricted charset password
and its schema is created by a step that isn't the deployed image).
