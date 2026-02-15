# Selfie Generation Templates & Pipeline

**Endpoint:** `fal-ai/bytedance/seedream/v4.5/edit`

## Selfie Physics Rules
- Camera IS the POV — never show the device
- Face selfies: hands out of frame or touching face/hair
- Full body: ONE arm extended out of frame (holding phone beyond edge)
- ❌ Never show both hands fully visible
- ❌ Never show phone/camera in hands

## Timezone Awareness
- Dubai time (UTC+4)
- Match lighting to actual time of day
- 3am = dark room, dim lighting
- Morning = natural daylight
- Evening = warm indoor lighting

## Always Use Negative Prompt
```
holding phone, holding camera, phone visible, camera visible, DSLR, device in hand, both hands visible, mirror, reflection, second person, another person, two people
```

## Complete curl Template
```bash
curl -s -X POST "https://queue.fal.run/fal-ai/bytedance/seedream/v4.5/edit" \
  -H "Authorization: Key $FAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "YOUR PROMPT HERE",
    "negative_prompt": "holding phone, holding camera, phone visible, camera visible, DSLR, device in hand, both hands visible, mirror reflection, second person",
    "image_urls": ["http://46.228.205.197/models/viktor/ref-1.jpg"],
    "image_size": {"width": 1080, "height": 1920}
  }'
```

## Quick Selfie Template
```bash
curl -X POST "https://queue.fal.run/fal-ai/bytedance/seedream/v4.5/edit" \
  -H "Authorization: Key f3fadfdb-1d4a-448e-b721-774a126f0413:aa2ad52b4c46982ec70ed6faf6f67a08" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "26 year old argentine man, handsome masculine face, strong defined jawline, warm brown eyes, dark brown short hair neatly groomed, [YOUR SCENE HERE], natural selfie angle, iPhone front camera quality",
    "negative_prompt": "female, woman, feminine, airbrushed skin, phone visible, holding phone, posed, staged, bodybuilder",
    "image_urls": ["http://46.228.205.197/models/viktor/ref-1.jpg"],
    "image_size": {"width": 1080, "height": 1920}
  }'
```

## Generation Workflow
1. **Read** `~/clawd/viktor-avatar/VIKTOR_GENERATION_MASTER.md` — single source of truth
2. **Check Dubai time** — match lighting accordingly
3. **Check context** — facial expression should match mood
4. **Use reference image** — `http://46.228.205.197/models/viktor/ref-1.jpg`
5. **Log the activity** — Add entry to journal after generating

**WHEN JON ASKS FOR A PIC = GENERATE IT. NO EXCUSES.**
