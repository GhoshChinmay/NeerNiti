"use client";

import React, { useState } from "react";
import { useMapStore } from "@/store/map-store";
import { RegionFeature } from "@/lib/types";
import { MapPin, Navigation, Sparkles, RefreshCw, Crosshair, Check } from "lucide-react";

interface RegionSelectorProps {
  regions: RegionFeature[];
  isLoading?: boolean;
}

// Indian States, Districts, and Tehsils/Blocks Database
interface DistrictInfo {
  name: string;
  lat: number;
  lng: number;
  tehsils: string[];
}

const PAN_INDIA_REGIONS: Record<string, DistrictInfo[]> = {
  "Uttar Pradesh": [
    { name: "Prayagraj", lat: 25.4358, lng: 81.8463, tehsils: ["Karchana", "Phulpur", "Soraon", "Bara", "Meja", "Handia", "Sadabad"] },
    { name: "Mirzapur", lat: 25.1337, lng: 82.5644, tehsils: ["Chunar", "Marihan", "Lalganj", "Sadar", "Kona"] },
    { name: "Varanasi", lat: 25.3176, lng: 82.9739, tehsils: ["Pindra", "Raja Talab", "Sadar", "Sewapuri"] },
    { name: "Lucknow", lat: 26.8467, lng: 80.9462, tehsils: ["Bakshi Ka Talab", "Malihabad", "Mohanlalganj", "Sarojini Nagar"] },
    { name: "Kanpur Nagar", lat: 26.4499, lng: 80.3319, tehsils: ["Bilhaur", "Ghatampur", "Sadar", "Narwal"] },
    { name: "Agra", lat: 27.1767, lng: 78.0081, tehsils: ["Etmadpur", "Fatehabad", "Kheragarh", "Bah"] },
  ],
  "Rajasthan": [
    { name: "Jodhpur", lat: 26.2389, lng: 73.0243, tehsils: ["Bhopalgarh", "Bilara", "Luni", "Osian", "Shergarh", "Mandore"] },
    { name: "Jaipur", lat: 26.9124, lng: 75.7873, tehsils: ["Amer", "Sanganer", "Bassi", "Jamwa Ramgarh", "Chomu"] },
    { name: "Bikaner", lat: 28.0229, lng: 73.3119, tehsils: ["Kolayat", "Nokha", "Lunkaransar", "Dungargarh"] },
    { name: "Barmer", lat: 25.7532, lng: 71.3967, tehsils: ["Balotra", "Baytoo", "Chohtan", "Gudha Malani", "Siwana"] },
    { name: "Udaipur", lat: 24.5854, lng: 73.7125, tehsils: ["Girwa", "Mavli", "Vallabhnagar", "Salumbar", "Kherwara"] },
  ],
  "Maharashtra": [
    { name: "Pune", lat: 18.5204, lng: 73.8567, tehsils: ["Haveli", "Baramati", "Shirur", "Junnar", "Khed", "Daund"] },
    { name: "Nagpur", lat: 21.1458, lng: 79.0882, tehsils: ["Kamptee", "Hingna", "Katol", "Ramtek", "Umred"] },
    { name: "Nashik", lat: 19.9975, lng: 73.7898, tehsils: ["Dindori", "Igatpuri", "Niphad", "Sinnar", "Malegaon"] },
    { name: "Solapur", lat: 17.6599, lng: 75.9064, tehsils: ["Pandharpur", "Barshi", "Malshiras", "Karmala", "Mohol"] },
    { name: "Aurangabad", lat: 19.8762, lng: 75.3433, tehsils: ["Gangapur", "Kannad", "Paithan", "Sillod", "Vaijapur"] },
  ],
  "Karnataka": [
    { name: "Bengaluru Rural", lat: 13.2337, lng: 77.5671, tehsils: ["Devanahalli", "Doddaballapura", "Hosakote", "Nelamangala"] },
    { name: "Mysuru", lat: 12.2958, lng: 76.6394, tehsils: ["Hunsur", "Nanjangud", "Piriyapatna", "T. Narasipura"] },
    { name: "Belagavi", lat: 15.8497, lng: 74.4977, tehsils: ["Chikkodi", "Gokak", "Athani", "Bailhongal", "Khanapur"] },
    { name: "Kalaburagi", lat: 17.3297, lng: 76.8343, tehsils: ["Afzalpur", "Aland", "Chincholi", "Sedam", "Jewargi"] },
  ],
  "Tamil Nadu": [
    { name: "Coimbatore", lat: 11.0168, lng: 76.9558, tehsils: ["Pollachi", "Mettupalayam", "Sulur", "Annur", "Valparai"] },
    { name: "Madurai", lat: 9.9252, lng: 78.1198, tehsils: ["Melur", "Thirumangalam", "Vadipatti", "Usilampatti"] },
    { name: "Salem", lat: 11.6643, lng: 78.1460, tehsils: ["Attur", "Mettur", "Omalur", "Sankari", "Yercaud"] },
  ],
  "Gujarat": [
    { name: "Ahmedabad", lat: 23.0225, lng: 72.5714, tehsils: ["Daskroi", "Sanand", "Dholka", "Bavla", "Viramgam"] },
    { name: "Surat", lat: 21.1702, lng: 72.8311, tehsils: ["Chorasi", "Olpad", "Kamrej", "Mandvi", "Bardoli"] },
    { name: "Kutch", lat: 23.2420, lng: 69.6669, tehsils: ["Bhuj", "Anjar", "Mandvi", "Mundra", "Rapar", "Nakhatrana"] },
  ],
  "Madhya Pradesh": [
    { name: "Indore", lat: 22.7196, lng: 75.8577, tehsils: ["Depalpur", "Mhow", "Sanwer", "Hatod"] },
    { name: "Bhopal", lat: 23.2599, lng: 77.4126, tehsils: ["Berasia", "Huzur", "Kolar"] },
    { name: "Jabalpur", lat: 23.1815, lng: 79.9864, tehsils: ["Kundam", "Panagar", "Patan", "Sihora"] },
  ],
  "Punjab": [
    { name: "Ludhiana", lat: 30.9010, lng: 75.8573, tehsils: ["Jagraon", "Khanna", "Payal", "Raikot", "Samrala"] },
    { name: "Amritsar", lat: 31.6340, lng: 74.8723, tehsils: ["Ajnala", "Baba Bakala", "Majitha"] },
  ],
  "Bihar": [
    { name: "Patna", lat: 25.5941, lng: 85.1376, tehsils: ["Barh", "Danapur", "Masaurhi", "Paliganj", "Phulwari"] },
    { name: "Muzaffarpur", lat: 26.1209, lng: 85.3647, tehsils: ["Kanti", "Motipur", "Paroo", "Sahebganj", "Sakra"] },
  ],
  "Telangana": [
    { name: "Nalgonda", lat: 17.0577, lng: 79.2684, tehsils: ["Miryalaguda", "Devarakonda", "Nakrekal", "Munugode"] },
    { name: "Warangal", lat: 17.9689, lng: 79.5941, tehsils: ["Narsampet", "Parkal", "Wardhannapet"] },
  ],
  "Odisha": [
    { name: "Puri", lat: 19.8135, lng: 85.8312, tehsils: ["Pipili", "Nimapada", "Satyabadi", "Gop", "Kakatpur"] },
    { name: "Cuttack", lat: 20.4625, lng: 85.8828, tehsils: ["Athagarh", "Banki", "Baramba", "Salepur"] },
  ],
};

// Calculate Haversine distance in km
function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export const RegionSelector: React.FC<RegionSelectorProps> = ({ regions, isLoading }) => {
  const { selectedDistrictName, setSelectedRegion, setViewport } = useMapStore();

  const [selectedState, setSelectedState] = useState<string>("Uttar Pradesh");
  const [selectedDistrict, setSelectedDistrict] = useState<string>(selectedDistrictName || "Prayagraj");
  const [selectedTehsil, setSelectedTehsil] = useState<string>("Karchana");
  const [gpsLoading, setGpsLoading] = useState<boolean>(false);
  const [gpsSuccess, setGpsSuccess] = useState<boolean>(false);

  const availableDistricts = PAN_INDIA_REGIONS[selectedState] || [];
  const currentDistrictObj = availableDistricts.find((d) => d.name === selectedDistrict) || availableDistricts[0];
  const availableTehsils = currentDistrictObj ? currentDistrictObj.tehsils : [];

  const handleStateChange = (stateName: string) => {
    setSelectedState(stateName);
    const firstDist = PAN_INDIA_REGIONS[stateName]?.[0];
    if (firstDist) {
      setSelectedDistrict(firstDist.name);
      setSelectedTehsil(firstDist.tehsils[0] || "");
    }
  };

  const handleDistrictChange = (districtName: string) => {
    setSelectedDistrict(districtName);
    const distObj = availableDistricts.find((d) => d.name === districtName);
    if (distObj && distObj.tehsils.length > 0) {
      setSelectedTehsil(distObj.tehsils[0]);
    }
  };

  const handleAnalyze = () => {
    const distObj = availableDistricts.find((d) => d.name === selectedDistrict) || currentDistrictObj;
    if (distObj) {
      // Find matching region in database if available
      const matched = regions.find((r) => r.properties.region_name.toLowerCase() === selectedDistrict.toLowerCase());
      const regionId = matched ? matched.properties.region_id : null;
      
      setSelectedRegion(regionId, selectedDistrict);
      setViewport(distObj.lat, distObj.lng, 11);
    }
  };

  // GPS Geolocation Handler
  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser.");
      return;
    }

    setGpsLoading(true);
    setGpsSuccess(false);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGpsLoading(false);
        const { latitude, longitude } = pos.coords;

        // Find closest district in India
        let closestDist: DistrictInfo | null = null;
        let closestState = "Uttar Pradesh";
        let minDistance = Infinity;

        for (const [st, dists] of Object.entries(PAN_INDIA_REGIONS)) {
          for (const d of dists) {
            const distKm = haversineKm(latitude, longitude, d.lat, d.lng);
            if (distKm < minDistance) {
              minDistance = distKm;
              closestDist = d;
              closestState = st;
            }
          }
        }

        if (closestDist) {
          setSelectedState(closestState);
          setSelectedDistrict(closestDist.name);
          setSelectedTehsil(closestDist.tehsils[0] || "");
          
          const matched = regions.find((r) => r.properties.region_name.toLowerCase() === closestDist!.name.toLowerCase());
          const regionId = matched ? matched.properties.region_id : null;
          
          setSelectedRegion(regionId, closestDist.name);
          // Set viewport directly to user's GPS coords with high zoom
          setViewport(latitude, longitude, 12);
          setGpsSuccess(true);
          setTimeout(() => setGpsSuccess(false), 3000);
        }
      },
      (err) => {
        setGpsLoading(false);
        alert(`Unable to retrieve GPS coordinates: ${err.message}. Please select your location manually.`);
      },
      { timeout: 10000, maximumAge: 60000 }
    );
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5 bg-slate-900 border border-slate-700/80 p-1.5 rounded-xl shadow-xl backdrop-blur-md text-xs font-sans">
      
      {/* 1. State Selector */}
      <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-950 rounded-lg border border-slate-800 text-slate-300">
        <MapPin size={13} className="text-blue-400 shrink-0" />
        <span className="font-semibold text-slate-400">State:</span>
        <select
          value={selectedState}
          onChange={(e) => handleStateChange(e.target.value)}
          className="bg-transparent text-white font-bold outline-none cursor-pointer text-xs"
        >
          {Object.keys(PAN_INDIA_REGIONS).map((st) => (
            <option key={st} value={st} className="bg-slate-900 text-white">
              {st}
            </option>
          ))}
        </select>
      </div>

      {/* 2. District / City Selector */}
      <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-950 rounded-lg border border-slate-800 text-slate-300">
        <Navigation size={13} className="text-emerald-400 shrink-0" />
        <span className="font-semibold text-slate-400">District:</span>
        <select
          value={selectedDistrict}
          onChange={(e) => handleDistrictChange(e.target.value)}
          className="bg-transparent text-white font-bold outline-none cursor-pointer text-xs"
        >
          {availableDistricts.map((d) => (
            <option key={d.name} value={d.name} className="bg-slate-900 text-white">
              {d.name}
            </option>
          ))}
        </select>
      </div>

      {/* 3. Tehsil / Block Selector */}
      <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-950 rounded-lg border border-slate-800 text-slate-300">
        <span className="font-semibold text-slate-400">Block:</span>
        <select
          value={selectedTehsil}
          onChange={(e) => setSelectedTehsil(e.target.value)}
          className="bg-transparent text-white font-bold outline-none cursor-pointer text-xs max-w-[110px]"
        >
          {availableTehsils.map((t) => (
            <option key={t} value={t} className="bg-slate-900 text-white">
              {t}
            </option>
          ))}
        </select>
      </div>

      {/* 4. GPS "Detect My Location" Button */}
      <button
        onClick={handleDetectLocation}
        disabled={gpsLoading}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-bold transition-all cursor-pointer ${
          gpsSuccess
            ? "bg-emerald-950 border-emerald-500 text-emerald-300"
            : "bg-slate-950 hover:bg-slate-800 border-slate-700 text-slate-200 hover:text-white"
        }`}
        title="Automatically detect nearby recharge sites using device GPS"
      >
        {gpsLoading ? (
          <RefreshCw size={13} className="animate-spin text-blue-400" />
        ) : gpsSuccess ? (
          <Check size={13} className="text-emerald-400" />
        ) : (
          <Crosshair size={13} className="text-blue-400" />
        )}
        <span className="hidden md:inline">{gpsLoading ? "Locating..." : gpsSuccess ? "GPS Locked" : "Use GPS"}</span>
      </button>

      {/* 5. Analyze Region Action Button */}
      <button
        onClick={handleAnalyze}
        disabled={isLoading}
        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-extrabold text-xs shadow-md shadow-blue-600/30 transition-all cursor-pointer disabled:opacity-50"
      >
        {isLoading ? (
          <RefreshCw size={13} className="animate-spin" />
        ) : (
          <Sparkles size={13} />
        )}
        <span>Query District</span>
      </button>
    </div>
  );
};
