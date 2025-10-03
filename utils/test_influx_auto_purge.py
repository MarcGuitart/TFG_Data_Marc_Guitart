"""
Script para probar la autogestión de datos en InfluxDB
"""
import os
import sys
import time
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient

# Configuración
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "admin_token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "tfg")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "pipeline")

def check_data_count():
    """Verifica la cantidad de datos en InfluxDB por unidad"""
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()
    
    print("\n" + "="*60)
    print("VERIFICACIÓN DE DATOS EN INFLUXDB")
    print("="*60)
    
    # Obtener todas las unidades
    flux_units = f'''
    import "influxdata/influxdb/schema"
    schema.tagValues(bucket: "{INFLUX_BUCKET}", tag: "unit")
    '''
    
    try:
        result = query_api.query(org=INFLUX_ORG, query=flux_units)
        units = [record.get_value() for table in result for record in table.records]
        
        if not units:
            print("⚠️  No hay unidades en la base de datos")
            return
        
        print(f"\n📊 Unidades encontradas: {len(units)}")
        print("-"*60)
        
        for unit in units:
            # Contar filas
            flux_count = f'''
            from(bucket: "{INFLUX_BUCKET}")
              |> range(start: 0)
              |> filter(fn: (r) => r._measurement == "telemetry")
              |> filter(fn: (r) => r.unit == "{unit}")
              |> count()
            '''
            count_result = query_api.query(org=INFLUX_ORG, query=flux_count)
            
            total_rows = 0
            for table in count_result:
                for record in table.records:
                    total_rows += record.get_value()
            
            # Obtener rango de fechas
            flux_range = f'''
            from(bucket: "{INFLUX_BUCKET}")
              |> range(start: 0)
              |> filter(fn: (r) => r._measurement == "telemetry")
              |> filter(fn: (r) => r.unit == "{unit}")
              |> keep(columns: ["_time"])
              |> sort(columns: ["_time"])
            '''
            range_result = query_api.query(org=INFLUX_ORG, query=flux_range)
            
            oldest = None
            newest = None
            for table in range_result:
                if table.records:
                    oldest = table.records[0].get_time()
                    newest = table.records[-1].get_time()
            
            print(f"\n🔹 Unidad: {unit}")
            print(f"   Filas totales: {total_rows}")
            if oldest and newest:
                print(f"   Más antiguo: {oldest}")
                print(f"   Más reciente: {newest}")
                age = datetime.now(oldest.tzinfo) - oldest
                print(f"   Antigüedad: {age}")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.close()

def test_retention():
    """Verifica que no haya datos más antiguos de 24h"""
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()
    
    cutoff = datetime.utcnow() - timedelta(hours=24)
    # usar RFC3339 sin microsegundos y añadir Z para UTC
    cutoff_iso = cutoff.replace(microsecond=0).isoformat() + "Z"
    
    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: 0, stop: time(v: "{cutoff_iso}"))
      |> filter(fn: (r) => r._measurement == "telemetry")
      |> count()
    '''
    
    try:
        result = query_api.query(org=INFLUX_ORG, query=flux)
        old_count = 0
        for table in result:
            for record in table.records:
                old_count += record.get_value()
        
        if old_count == 0:
            print("✅ No hay datos más antiguos de 24h (retención funcionando)")
        else:
            print(f"⚠️  Encontrados {old_count} puntos más antiguos de 24h")
            
    except Exception as e:
        print(f"❌ Error verificando retención: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    print("\n🧪 Iniciando pruebas de autogestión de InfluxDB...")
    
    while True:
        check_data_count()
        test_retention()
        
        print("\n⏳ Esperando 30 segundos para próxima verificación...")
        print("   (Ctrl+C para detener)")
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n\n👋 Pruebas finalizadas")
            sys.exit(0)