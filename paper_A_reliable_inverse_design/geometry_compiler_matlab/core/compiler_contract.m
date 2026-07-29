function contract = compiler_contract()
%COMPILER_CONTRACT Immutable bootstrap contract for schema version 1.0.
    contract = struct();
    contract.schemaVersion = '1.0';
    contract.descriptorNames = {'relativeVolume', 'relativeArea', ...
        'thickness', 'poreDiameter', 'areaMean'};
    contract.requiredLevels = [96, 128, 160];
end
