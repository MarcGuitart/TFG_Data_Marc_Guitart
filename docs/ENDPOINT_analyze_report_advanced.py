
# Endpoint para análisis avanzado con IA
# Se agregará en services/orchestrator/app.py antes del final del archivo


@app.post("/api/analyze_report_advanced/{id}")
async def analyze_report_advanced(id: str, request_body: dict = None):
    """
    Análisis avanzado con IA usando:
    1. Pipeline report (datos de la última ejecución)
    2. Export report opcional (CSV con histórico de weights y rankings)
    
    Proporciona análisis profundo y contextualizado.
    """
    try:
        from groq import Groq
        import csv
        import json
        
        # Validar request
        if not request_body:
            raise ValueError("Request body required")
        
        pipeline_report = request_body.get("pipeline_report", {})
        export_report_csv = request_body.get("export_report")
        export_filename = request_body.get("export_filename", "")
        
        # Configurar Groq API
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GROQ_API_KEY not configured. Get free API key at: https://console.groq.com/keys"
            )
        
        # ===== Preparar contexto del pipeline report =====
        pipeline_context = f"""
## Pipeline Execution Report

**Series ID:** {pipeline_report.get('id', 'Unknown')}
**Total Data Points:** {pipeline_report.get('total', 0)}

### Data Points Sample (first 5):
"""
        points = pipeline_report.get('points', [])[:5]
        for i, p in enumerate(points, 1):
            pipeline_context += f"\n{i}. Timestamp: {p.get('timestamp', 'N/A')}"
            pipeline_context += f"\n   - Real value: {p.get('var', 'N/A')}"
            pipeline_context += f"\n   - Prediction: {p.get('prediction', 'N/A')}"
            pipeline_context += f"\n   - Chosen model: {p.get('chosen_model', 'N/A')}"
            pipeline_context += f"\n   - Error: {p.get('chosen_error_abs', 'N/A')} (rel: {p.get('chosen_error_rel', 'N/A')}%)"
        
        # ===== Preparar contexto del export report =====
        export_context = ""
        if export_report_csv:
            export_context = f"\n\n## Historical Export Report\n\n**File:** {export_filename}\n\n### CSV Preview (first 10 rows):\n\n```\n"
            csv_lines = export_report_csv.split('\n')
            # Header + primeras 10 filas
            preview_lines = csv_lines[:11]
            export_context += '\n'.join(preview_lines)
            export_context += "\n```\n"
            
            # Análisis estadístico del CSV
            try:
                reader = csv.DictReader(export_report_csv.split('\n'))
                rows = list(reader)
                
                if rows:
                    # Extraer nombres de modelos
                    model_names = [col.replace('w_', '') for col in rows[0].keys() if col.startswith('w_')]
                    
                    # Estadísticas de selección (chosen_by_error)
                    selections = {}
                    weights_evolution = {m: [] for m in model_names}
                    rankings_by_model = {m: [] for m in model_names}
                    
                    for row in rows:
                        chosen = row.get('chosen_by_error', '')
                        if chosen:
                            selections[chosen] = selections.get(chosen, 0) + 1
                        
                        for model in model_names:
                            w_key = f'w_{model}'
                            r_key = f'rank_{model}'
                            if w_key in row:
                                try:
                                    weights_evolution[model].append(float(row[w_key]))
                                except:
                                    pass
                            if r_key in row:
                                try:
                                    rankings_by_model[model].append(int(row[r_key]))
                                except:
                                    pass
                    
                    # Análisis de selección
                    export_context += f"\n### Model Selection Summary ({len(rows)} steps):\n\n"
                    for model in sorted(selections.keys(), key=lambda m: selections[m], reverse=True):
                        pct = (selections[model] / len(rows)) * 100
                        export_context += f"- **{model}**: {selections[model]} times ({pct:.1f}%)\n"
                    
                    # Análisis de pesos
                    export_context += f"\n### Weight Evolution:\n\n"
                    for model in model_names:
                        if weights_evolution[model]:
                            initial = weights_evolution[model][0]
                            final = weights_evolution[model][-1]
                            avg = sum(weights_evolution[model]) / len(weights_evolution[model])
                            max_w = max(weights_evolution[model])
                            min_w = min(weights_evolution[model])
                            export_context += f"\n**{model}:**\n"
                            export_context += f"  - Initial: {initial:.4f} → Final: {final:.4f}\n"
                            export_context += f"  - Average: {avg:.4f} (Range: {min_w:.4f} to {max_w:.4f})\n"
                    
                    # Análisis de rankings
                    export_context += f"\n### Average Rankings (lower is better):\n\n"
                    for model in model_names:
                        if rankings_by_model[model]:
                            avg_rank = sum(rankings_by_model[model]) / len(rankings_by_model[model])
                            export_context += f"- **{model}**: {avg_rank:.2f}\n"
            
            except Exception as e:
                logger.warning(f"Error parsing export CSV: {e}")
                export_context += f"\n(Could not fully parse CSV: {str(e)})"
        
        # ===== Crear prompt contextualizado para IA =====
        analysis_prompt = f"""
You are an expert data scientist specializing in ensemble learning, time series forecasting, and adaptive prediction systems.

Analyze the following report in DEEP DETAIL with specific, actionable insights:

{pipeline_context}

{export_context}

---

Please provide a comprehensive analysis covering:

1. **Model Performance Patterns**
   - Which models performed best in different periods?
   - Are there specific data characteristics where certain models excel?
   - How consistent is each model's performance?

2. **Weight Adaptation Quality**
   - Is the weight evolution system working effectively?
   - Are weights converging to stable values or oscillating?
   - Do the weights correlate with actual model performance?

3. **Selection Decisions**
   - How frequently was each model selected?
   - Is there diversity in model selection or dominance by one model?
   - Are selection patterns correlated with data characteristics?

4. **System Stability & Convergence**
   - Is the ensemble showing signs of overfitting to certain patterns?
   - How responsive is the system to changes in data characteristics?
   - Recommendations for weight decay, learning rates, or system parameters?

5. **Actionable Insights**
   - What specific improvements could enhance predictions?
   - Should any models be removed, replaced, or reweighted?
   - Any data quality issues or anomalies to investigate?

Provide specific numbers, percentages, and data-driven evidence for all claims.
Use markdown formatting for clarity.
"""
        
        # ===== Llamar a Groq API =====
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert data scientist in time series forecasting and ensemble learning. Provide deep, quantitative, actionable analysis based on the actual data provided."
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ],
            max_tokens=4000,
            temperature=0.7,
        )
        
        analysis = response.choices[0].message.content
        
        return {
            "success": True,
            "analysis": analysis,
            "series_id": id,
            "analysis_type": "advanced",
            "pipeline_points": len(points),
            "export_file": export_filename if export_report_csv else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in advanced AI analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")
