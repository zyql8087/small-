function contract = compiler_contract()
%COMPILER_CONTRACT Immutable bootstrap contract for schema version 1.0.
    contract = struct();
    contract.schemaVersion = '1.0';
    contract.descriptorNames = {'relativeVolume', 'relativeArea', ...
        'thickness', 'poreDiameter', 'areaMean'};
    contract.requiredLevels = [96, 128, 160];
    contract.descriptorDefinitionSha256 = ...
        '9e31513211e50a5251a91cecd303947939db023c1713ea3900c5920dbf98003d';
    contract.legacyCandidateDescriptorDefinitionSha256 = ...
        '2f59976c74cc88eac66c43a56e242f50f28aff0e71be8d752a481c05a4a2d9c9';
    contract.parameterDomainManifestSha256 = ...
        '671e0c081f8d50e1060a1cfdb4e10d70b662319582f2922231400ba56dd7bd2a';
    contract.thresholdProfile = ...
        'piecewise_linear_knots_z_over_l_0_1_2';
    contract.cellSizeProfile = ...
        'gamma(z_over_l)=1.5+z_over_l/w';
    contract.gyroidFieldVersion = ...
        'small-si-s6-s9-candidate-v1';
    contract.solidConvention = 'sheet_band';
    contract.geometryDefinition = ...
        'continuous_sheet_gyroid_intersect_hard_box';
    contract.validationStage = 'M03_GEOMETRY_MESH';
    contract.descriptorValidationStage = 'M04_DUAL_DESCRIPTORS';
    contract.betaBox = 1.0;
    contract.isosurfaceLevel = 0.0;
    contract.gridConvention = 'cell_centered_half_step_exterior';
    contract.requestSchemaVersion = '1.0';
    contract.requestFields = {'schema_version', 'request_id', 'method', ...
        'c0', 'c1', 'c2', 'w', 'resolution', 'output_dir'};
end
