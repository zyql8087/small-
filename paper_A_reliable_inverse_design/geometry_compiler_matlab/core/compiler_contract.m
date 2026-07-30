function contract = compiler_contract()
%COMPILER_CONTRACT Immutable bootstrap contract for schema version 1.0.
    contract = struct();
    contract.schemaVersion = '1.0';
    contract.descriptorNames = {'relativeVolume', 'relativeArea', ...
        'thickness', 'poreDiameter', 'areaMean'};
    contract.requiredLevels = [96, 128, 160];
    contract.descriptorDefinitionSha256 = ...
        '3031842d0bfb661d134e087e9e200093b41ed2af724b361d530a17c8047ef94d';
    contract.parameterDomainManifestSha256 = ...
        'd152142ea2ff5cc6aa55ee366a71483f621fdd618117b87467d69137049c2eb2';
end
