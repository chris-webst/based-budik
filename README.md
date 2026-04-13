# based-budik
Budík, co tě vzbudí přesně načas podle aktuální dopravní situace.

## Jak funguje

1. **Nastavení budíku** - definuješ dva časy:
   - **Čas buzení (normální)** - pokud vlak nejede se zpožděním
   - **Čas buzení (zpožděný spoj)** - pokud vlak má větší zpoždění než je tvá tolerance

2. **Automatická kontrola** - scheduler se každou minutu podívá, zda:
   - Je dnes aktivní den pro tvůj budík
   - Je čas na kontrolu zpoždění (CHECK_BEFORE_MINUTES před safe_wake_time)

3. **Rozhodnutí**:
   - Zkontroluje zpoždění vlaku z API
   - Pokud se API nepodaří nebo je zpoždění > tolerance → zvoní v `safe_wake_time`
   - Pokud je ok a zpoždění ≤ tolerance → zvoní v `base_wake_time`

4. **Probuzení** - nastaví Mac probuzení přes `pmset` a přehraje zvuk

## Příklad

```
Vlak v 8:24 (tolerance 2 min)
Normální buďo: 7:20
Zpožděný buďo: 6:50
CHECK_BEFORE_MINUTES: 5

→ v 6:45 proběhne kontrola
→ pokud delay ≤ 2 min: probuzení v 7:20
→ pokud delay > 2 min nebo API fail: probuzení v 6:50
```

## Nastavení

### config.py
- `CHECK_BEFORE_MINUTES` - kolik minut před `safe_wake_time` se kontroluje zpoždění (default: 5 min)

### Každý budík má:
- `base_wake_time` - standardní čas buzení
- `safe_wake_time` - čas buzení pro případ zpoždění
- `delay_tolerance_minutes` - jaké maximální zpoždění akceptuješ (tolerancia)
- `days_of_week` - dny, kdy je budík aktivní

