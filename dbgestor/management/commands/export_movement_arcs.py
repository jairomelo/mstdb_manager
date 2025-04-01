import requests
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Command(BaseCommand):
    help = "Exports movement arcs from travel trajectories (only enslaved persons)"

    # Retrieve data from local API to avoid rate limiting
    API_URL = f"{os.getenv('LOCAL_API_ENDPOINT')}/travel-trajectories"

    def handle(self, *args, **options):
        all_results = []
        url = self.API_URL

        self.stdout.write("Fetching data from API...")

        while url:
            # avoid exhausting the API
            #time.sleep(2.5)
            
            try:
                res = requests.get(url)
                res.raise_for_status()
                data = res.json()
                url = data.get("next")
                all_results.extend([
                    r for r in data["results"]
                    if r["polymorphic_ctype"] == "Dbgestor | persona esclavizada"
                ])
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error fetching data: {e}"))
                raise

        self.stdout.write(f"Fetched {len(all_results)} enslaved persons")

        arcs = []
        transitions = defaultdict(int)

        for person in all_results:
            
            traj = person.get("trayectoria", [])
            traj = sorted(traj, key=lambda x: (x.get("fecha"), x.get("ordinal", 0)))



            for i in range(len(traj) - 1):
                from_loc = traj[i]["lugar"]
                to_loc = traj[i + 1]["lugar"]
                
                if from_loc["lat"] is None or to_loc["lat"] is None:
                    continue

                # Movement arc (per person)
                arc = {
                    "persona_id": person["persona_id"],
                    "idno": person["persona_idno"],
                    "name": person["nombre_normalizado"],
                    "step": i + 1,
                    "date": traj[i].get("fecha"),
                    "year": traj[i].get("fecha")[:4] if traj[i].get("fecha") else None,
                    "from": {
                        "name": from_loc["nombre_lugar"],
                        "lat": float(from_loc["lat"]),
                        "lon": float(from_loc["lon"])
                    },
                    "to": {
                        "name": to_loc["nombre_lugar"],
                        "lat": float(to_loc["lat"]),
                        "lon": float(to_loc["lon"])
                    }
                }
                arcs.append(arc)
                
                # Aggregate transitions
                key = (
                    from_loc["nombre_lugar"], float(from_loc["lat"]), float(from_loc["lon"]),
                    to_loc["nombre_lugar"], float(to_loc["lat"]), float(to_loc["lon"])
                )
                transitions[key] += 1

        self.stdout.write(f"Generated {len(arcs)} arcs")

        # Save per-person arcs
        output_path = Path(settings.BASE_DIR) / "staticfiles" / "mdb" / "data" / "trayectorias_arcs.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(arcs, f, ensure_ascii=False, indent=2)
        
        # Save aggregated flows
        aggregated = []
        for (from_name, from_lat, from_lon, to_name, to_lat, to_lon), count in transitions.items():
            aggregated.append({
                "from": { "name": from_name, "lat": from_lat, "lon": from_lon },
                "to": { "name": to_name, "lat": to_lat, "lon": to_lon },
                "count": count
            })

        agg_path = Path(settings.BASE_DIR) / "staticfiles" / "mdb" / "data" / "trayectorias_aggregated.json"
        with open(agg_path, "w", encoding="utf-8") as f:
            json.dump(aggregated, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f"Saved {len(arcs)} arcs to {output_path}"))
        self.stdout.write(self.style.SUCCESS(f"Saved {len(aggregated)} aggregated flows to {agg_path}"))
