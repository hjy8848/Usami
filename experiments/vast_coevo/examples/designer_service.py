"""Run/replay the explicitly versioned CloudOps Designer–Service protocol."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from integrations.usami.designer.cli import main
if __name__=='__main__':raise SystemExit(main())
