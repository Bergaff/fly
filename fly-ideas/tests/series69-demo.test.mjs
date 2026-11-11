import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';

const vite=await createServer({configFile:new URL('../vite.config.ts',import.meta.url).pathname,server:{middlewareMode:true},appType:'custom'});
test('демонстратор серии 69 строго читает playback, activity, state и metrics',async()=>{
  try {
    const trajectoryLib=await vite.ssrLoadModule('/src/lib/wing-trajectory.ts');
    const demoLib=await vite.ssrLoadModule('/src/lib/series69-demo.ts');
    const trajectory=trajectoryLib.initialTrajectory;
    const samples=Array.from({length:51},(_,i)=>({t:i/25,teacher_deg:trajectoryLib.interpolate(i/25,trajectory),prediction_deg:[0,0,0,0,0,0]}));
    const playback=JSON.stringify({schema:'fly-wings-result-v1',fps:25,duration_s:2,trajectory,samples,method:'fixture'});
    const header=['time_s',...Array.from({length:24},(_,i)=>`compact_${String(i).padStart(2,'0')}`),...Array.from({length:96},(_,i)=>`rich_level_${String(i).padStart(3,'0')}`),...Array.from({length:96},(_,i)=>`rich_delta_${String(i).padStart(3,'0')}`)];
    const activity=[header.join(','),...Array.from({length:51},(_,i)=>[i/25,...Array.from({length:216},(_,j)=>Math.sin(i+j))].join(','))].join('\n');
    const metrics=JSON.stringify({holdout_index:1,delay_s:.5,state_unchanged_during_delay:true,zero:{rmse_rad:.3},conditions:{normal:{compact:{rmse_rad:.2},rich:{rmse_rad:.19}}}});
    const states=JSON.stringify({compact:Array(72).fill(0),rich:Array(72).fill(1),updates_during_delay:0});
    const parsed=demoLib.parseSeries69Demo({folder:'x',compact:playback,rich:playback,activity,metrics,states});
    assert.equal(parsed.activity.richLevel.length,51);assert.equal(parsed.activity.richLevel[0].length,96);
    assert.equal(parsed.states.rich.length,72);assert.equal(parsed.metrics.delay_s,.5);
    assert.throws(()=>demoLib.parseAblationActivity(activity.replace('compact_00','bad')),/24 compact/);
    assert.throws(()=>demoLib.parseSeries69Demo({folder:'x',compact:playback,rich:playback,activity,metrics,states:JSON.stringify({compact:[],rich:[],updates_during_delay:1})}),/internal_states/);
  } finally { await vite.close(); }
});
