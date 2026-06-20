import pymysql, os
from dotenv import load_dotenv
load_dotenv()

url = os.environ.get('MYSQL_URL','').replace('mysql+pymysql://','').replace('mysql://','')
creds, rest = url.split('@')
user, password = creds.split(':', 1)
hostport, db = rest.split('/', 1)
host, port = hostport.rsplit(':', 1)

conn = pymysql.connect(host=host, port=int(port), user=user, password=password, database=db, charset='utf8mb4', autocommit=True)
cur = conn.cursor()

cur.execute("SET FOREIGN_KEY_CHECKS = 0")

grupos_borrar = [26, 25, 32, 27]
cur.execute("DELETE FROM aliment_descriptions WHERE aliment_id IN (SELECT id FROM aliments WHERE group_food_id IN (%s,%s,%s,%s))", grupos_borrar)
print(f"Descripciones borradas: {cur.rowcount}")

cur.execute("DELETE FROM aliments WHERE group_food_id IN (%s,%s,%s,%s)", grupos_borrar)
print(f"Alimentos borrados: {cur.rowcount}")

cur.execute("DELETE FROM group_foods WHERE id NOT IN (SELECT DISTINCT group_food_id FROM aliments WHERE group_food_id IS NOT NULL)")
print(f"Grupos vacios borrados: {cur.rowcount}")

cur.execute("SET FOREIGN_KEY_CHECKS = 1")

cur.execute("SELECT COUNT(*) FROM aliments")
print(f"\nAlimentos restantes: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM group_foods")
print(f"Grupos restantes: {cur.fetchone()[0]}")
conn.close()
