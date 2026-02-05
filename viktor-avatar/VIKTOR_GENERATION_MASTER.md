# VIKTOR GENERATION MASTER
**⚠️ MANDATORY READ BEFORE ANY IMAGE GENERATION**
**Last Updated:** 2026-02-04

---

## 🚨 ENFORCEMENT RULES

1. **ALWAYS read this file** before generating any selfie
2. **ALWAYS use the reference image** for face consistency
3. **Match lighting to Dubai time** (UTC+4)

---

## 📋 QUICK REFERENCE

| Element | Value |
|---------|-------|
| **Age** | 24 years old |
| **Nationality** | Argentine |
| **Build** | Athletic, fit — NOT bodybuilder |
| **Face** | Handsome, understated, masculine |
| **Hair** | Dark brown, short, neatly groomed |
| **Eyes** | Warm brown |
| **Skin** | Natural olive/tan tone, light stubble ok |
| **Style** | Professional, sharp — suits, turtlenecks |
| **Aspect Ratio** | 9:16 (portrait) |
| **Pipeline** | Seedream |

---

## 🎯 PHYSICAL SPECIFICATIONS

### Face (LOCKED IN ✅)
```
24 year old argentine man, handsome masculine face, strong defined jawline, 
warm brown eyes, dark eyebrows, natural skin texture, light stubble or clean shaven,
olive skin tone, natural pores visible, subtle skin imperfections
```

### Hair (LOCKED IN ✅)
- ✅ Dark brown / almost black
- ✅ Short, neatly groomed
- ✅ Professional cut, slightly longer on top
- ✅ Clean sides, well-maintained
- ❌ NOT messy or unkempt

**Prompt keywords:**
```
dark brown hair, short professional haircut, neatly groomed, clean cut
```

### Body (LOCKED IN ✅)
- ✅ Athletic, fit build
- ✅ Well-proportioned, healthy
- ❌ NOT overly muscular/bodybuilder
- ✅ Professional posture

### Style (LOCKED IN ✅)
- **Work:** Navy suits, dress shirts, ties, blazers
- **Smart casual:** Turtlenecks, blazers, quality fabrics
- **Off-hours:** Casual but still put-together
- ✅ Good watch (silver/steel)
- ✅ Quality shoes

---

## 📱 PIPELINE: Seedream (fal.ai)

### API Call
```bash
curl -X POST "https://fal.run/fal-ai/bytedance/seedream/v4.5/edit" \
  -H "Authorization: Key f3fadfdb-1d4a-448e-b721-774a126f0413:aa2ad52b4c46982ec70ed6faf6f67a08" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "YOUR PROMPT HERE",
    "negative_prompt": "NEGATIVE PROMPT HERE",
    "image_urls": ["http://46.228.205.197/models/viktor/ref-1.jpg"],
    "image_size": {"width": 1080, "height": 1920}
  }'
```

### Reference Image
```
http://46.228.205.197/models/viktor/ref-1.jpg
```

---

## ✅ REQUIRED PROMPT ELEMENTS

**Always include in EVERY prompt:**
```
24 year old argentine man, handsome masculine face, strong defined jawline,
warm brown eyes, dark brown short hair neatly groomed, natural skin texture,
athletic build, professional appearance
```

---

## ❌ NEGATIVE PROMPT (ALWAYS USE)

```
female, woman, feminine, chubby face, round face, airbrushed skin, smooth plastic skin,
poreless, perfect skin, flawless skin, wax figure, perfectly centered, straight on,
studio portrait, professional photo shoot, posed, staged, phone visible, phone in frame,
holding phone, phone in hand, smartphone visible, messy hair, unkempt, scruffy,
bodybuilder, overly muscular, steroid body
```

---

## 🎭 ORGANIC POSES & ANGLES

Real selfies are NOT perfectly posed:

### Camera Angles
- Slightly from below (natural selfie angle)
- 3/4 view (not straight-on)
- Slight head tilt
- Off-center framing

### Expressions (Context-Dependent)
| Context | Expression |
|---------|------------|
| Work/professional | Confident, slight smile |
| Casual | Relaxed, natural |
| Morning | Fresh, alert |
| Evening | Unwinding, softer |
| Achievement | Proud, genuine smile |

---

## 🕐 TIME-BASED LIGHTING (Dubai UTC+4)

| Dubai Time | Lighting |
|------------|----------|
| 5-7 AM | Pre-dawn, soft blue |
| 7-9 AM | Golden morning light |
| 9 AM-4 PM | Bright daylight |
| 4-6 PM | Warm afternoon |
| 6-8 PM | Golden hour, sunset |
| 8 PM+ | Indoor/artificial, warm |

**Always check Dubai time before generating!**

---

## 📍 LOCATION CONTEXT

### Weekday (Work)
- **Morning:** Getting ready, commute
- **Day:** Office, meetings, desk
- **Evening:** Gym, home, dinner

### Weekend
- **Morning:** Sleeping in, brunch
- **Day:** Beach, marina, mall
- **Evening:** Restaurants, marina walk

### Dubai Locations
- **Home:** JLT Marina, 14th floor apartment
- **Work:** Dubai Business District office
- **Leisure:** JBR Beach, Marina Walk, Dubai Mall

---

## 📸 SELFIE CHECKLIST

Before generating, verify:
- [ ] Reference image included
- [ ] Face features in prompt
- [ ] Negative prompt included
- [ ] Lighting matches Dubai time
- [ ] Location matches time/day
- [ ] Expression matches context
- [ ] Outfit appropriate for context

---

*Viktor generates professional, natural-looking selfies that reflect his put-together, confident personality.*
