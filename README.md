# محترف الإخراج — Mohtaref Al Ekhraj

Streamlit cinematic AI directing system with Runway connection, safe mode, scene/shot planning, visual libraries, storyboard mode, Yemeni identity, realism controls, preview workflow, long scene timeline, and project save/load/export.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 3000
```

## Environment
Set Runway API key:
```env
RUNWAYML_API_SECRET=your_key_here
```

## Notes
- Safe Mode is on by default.
- Runway video duration is limited to 4/6/8 seconds.
- Shot planning duration can be 1-10 seconds.
- Long scenes are built by splitting into short shots.
