import React, { createContext, useContext, useState } from 'react';

import { useNavigate } from 'react-router-dom';

const ScanContext = createContext(null);

export const PRESET_DATA = {

  GENUINE_AMARTEM: {

    id: 'preset-001',

    productName: 'Amartem Soft Gel',

    nafdacNumber: 'A4-0321',

    batchNumber: 'BN-88412',

    expiryDate: '12/2026',

    situation: 'BEFORE_BUYING',

    type: 'GENUINE',

  },

  REGISTRY_MISMATCH: {

    id: 'preset-002',

    productName: 'Betaclox 500mg',

    nafdacNumber: '04-2191-ERR',

    batchNumber: 'BN-10293',

    expiryDate: '08/2025',

    situation: 'BEFORE_BUYING',

    type: 'MISMATCH',

  },

  BATCH_CLONE: {

    id: 'preset-003',

    productName: 'Emzor Paracetamol',

    nafdacNumber: '04-0123',

    batchNumber: 'BN-KANO-99',

    expiryDate: '01/2026',

    situation: 'ALREADY_BOUGHT',

    type: 'CLONE',

  },

  COMMUNITY_REPORTED: {

    id: 'preset-004',

    productName: 'Lonart DS',

    nafdacNumber: 'A4-9981',

    batchNumber: 'BN-TF-441',

    expiryDate: '04/2025',

    situation: 'BEFORE_BUYING',

    type: 'COMMUNITY_ALERT',

  },

  SON_REGULATED: {

    id: 'preset-005',

    productName: 'Coleman 2.5mm Wire',

    nafdacNumber: 'SON-CAP-8812',

    batchNumber: 'BN-COL-112',

    expiryDate: 'N/A',

    situation: 'BEFORE_BUYING',

    type: 'SON_STANDARD',

  },

  UNKNOWN_ITEM: {

    id: 'preset-006',

    productName: 'Bio-Glow Cream',

    nafdacNumber: 'UNVERIFIED',

    batchNumber: 'BN-BIO-009',

    expiryDate: '11/2025',

    situation: 'ALREADY_BOUGHT',

    type: 'AUTONOMOUS_SEARCH',

  },

};

export const ScanProvider = ({ children }) => {

  const [currentScan, setCurrentScan] = useState(null);

  const [situation, setSituation] = useState('BEFORE_BUYING');

  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const navigate = useNavigate();

  const startScan = (payload) => {

    setIsAnalyzing(true);

    const scanId = payload.id || `scan-${Date.now()}`;

    const scanPayload = { ...payload, id: scanId, situation };

    setCurrentScan(scanPayload);

    navigate('/checking');

  };

  const loadPreset = (presetKey) => {

    const selected = PRESET_DATA[presetKey];

    if (!selected) return;

    setSituation(selected.situation);

    startScan(selected);

  };

  return (

    <ScanContext.Provider

      value={{

        currentScan,

        setCurrentScan,

        situation,

        setSituation,

        isAnalyzing,

        setIsAnalyzing,

        startScan,

        loadPreset,

      }}

    >

      {children}

    </ScanContext.Provider>

  );

};

export const useScan = () => {

  const context = useContext(ScanContext);

  if (!context) {

    throw new Error('useScan must be used within a ScanProvider');

  }

  return context;

};
