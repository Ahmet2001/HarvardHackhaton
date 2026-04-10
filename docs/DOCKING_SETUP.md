# Docking Tool Setup

Bıdık integrates with real command-line tools. It does not fabricate docking output.

Ligands can be stored from PubChem name lookup, pasted SMILES, uploaded MOL/MOL2/SDF files, or uploaded PDBQT files. PubChem lookup gives the app a convenient public source for SMILES, but it is not a substitute for curated ligand preparation.

## Required for full docking

- Open Babel executable available as `obabel`
- AutoDock Vina executable available as `vina`

Override paths with:

```bash
export BIDIK_OBABEL_BINARY=/path/to/obabel
export BIDIK_VINA_BINARY=/path/to/vina
```

## What the MVP does

1. Downloads a PDB file from RCSB PDB.
2. Cleans receptor records by keeping receptor `ATOM` lines and removing common water residues.
3. Converts receptor PDB to PDBQT through Open Babel.
4. Converts ligand SMILES/MOL/MOL2/SDF to PDBQT through Open Babel, or accepts uploaded PDBQT directly.
5. Estimates a docking box from receptor coordinates when binding-site coordinates are missing.
6. Runs AutoDock Vina with user-configured box, exhaustiveness, modes, and energy range.
7. Parses Vina log scores and writes a Markdown report.

## Scientific caveats

The automatic receptor cleanup and autoboxing are MVP defaults, not a validated protocol. Real studies should use curated receptor preparation, protonation-state decisions, ligand tautomer/protomer handling, binding-site definition, controls, repeatability checks, and expert review of poses.
