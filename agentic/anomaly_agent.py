def anomaly_agent_node(state):
    df = state["_df"]
    results = []
    for column in df.select_dtypes(include="number").columns:
        s = df[column].dropna()
        if len(s) < 4:
            continue
        q1, q3 = s.quantile(.25), s.quantile(.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5*iqr, q3 + 1.5*iqr
        count = int(((df[column] < lower) | (df[column] > upper)).fillna(False).sum())
        if count:
            results.append({"column": str(column), "outlier_count": count,
                            "lower_bound": float(lower), "upper_bound": float(upper)})
    text = ("IQR-based anomaly detection found potential outliers in: " +
            ", ".join(x["column"] for x in results) + ".") if results else "No IQR-based numeric outliers were detected."
    return {"anomaly_result": results, "analysis": text}
