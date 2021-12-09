import argparse
import pandas as pd
import time
from golf_game import GolfGame

d = { 'map': [], 'seed': [], 'skill': [], 'score': [], 'time': [], 'state': [] }

###########################################
### CHANGE THESE TO RUN DIFFERENT TESTS ###
###########################################
maps = ['maps/g7/complex2.json', 'maps/g8/backtrack.json', 'maps/g2/skinny.json', 'maps/g9/layup.json']
skills = [10, 40, 70, 100]
seeds = [32423, 23894, 581, 8, 102]

num_tests = len(maps) * len(skills) * len(seeds)
player_list = ('5')

test_i = 1
for map in maps:
  for skill in skills:
    for seed in seeds:
      print('#####\nRunning test {} of {}\n#####\n'.format(test_i, num_tests))
      args = argparse.Namespace(
        address='127.0.0.1',
        automatic=True,
        disable_logging=False,
        disable_timeout=True,
        log_path='log',
        map=map,
        no_browser=True,
        no_gui=True,
        players=['5'],
        port=8080,
        seed=seed,
        skill=skill
      )
      golf_game = GolfGame(player_list, args)
      golf_game.play_all()
      result = golf_game.get_state()
      d['map'].append(map)
      d['seed'].append(seed) 
      d['skill'].append(skill)
      d['score'].append(result['scores'][0])
      d['time'].append(result['total_time_sorted'][0][1])
      d['state'].append(result['player_states'][0])
      print('map: {}\nseed: {}\nskill: {}\nscore: {}\ntime: {}\nstate: {}\n'.format(
        map, seed, skill, result['scores'][0], result['total_time_sorted'][0][1], result['player_states'][0]
      ))
      test_i += 1

filename = 'g5-test ({}).csv'.format(time.strftime('%c'))
print('saving file "' + filename + '"')
df = pd.DataFrame(data=d)
df.to_csv(filename, index=False)