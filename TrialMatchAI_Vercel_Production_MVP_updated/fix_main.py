with open('backend/app/main.py', 'rb') as f:
    content = f.read()

idx = content.rfind(b'return {"processed":processed}')
if idx != -1:
    good_content = content[:idx + len(b'return {"processed":processed}')]
    with open('backend/app/main.py', 'wb') as f:
        f.write(good_content)
        f.write(b'\n\nfrom fastapi.responses import HTMLResponse\n')
        f.write(b'from backend.app.ai.graph_rag import generate_graph_rag_reasoning\n')
        f.write(b'from backend.app.graph_builder import generate_patient_graph_html\n\n')
        f.write(b'@app.get("/api/patients/{patient_id}/graph_rag/{match_id}")\n')
        f.write(b'def get_graph_rag(patient_id: int, match_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):\n')
        f.write(b'    reasoning = generate_graph_rag_reasoning(db, match_id)\n')
        f.write(b'    return {"match_id": match_id, "patient_id": patient_id, "reasoning": reasoning}\n\n')
        f.write(b'@app.get("/api/patients/{patient_id}/graph", response_class=HTMLResponse)\n')
        f.write(b'def get_patient_graph(patient_id: int, db: Session = Depends(get_db)):\n')
        f.write(b'    return HTMLResponse(content=generate_patient_graph_html(db, patient_id))\n')
