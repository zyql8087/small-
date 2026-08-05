function text = canonical_descriptor_text(profiles)
%CANONICAL_DESCRIPTOR_TEXT Serialize M04 values in fixed profile/name order.

    errorId = 'MATLABGyroid:DescriptorProfileInvalid';
    profileNames = {'legacy_small', 'physical_m04'};
    descriptorNames = {'relativeVolume', 'relativeArea', 'thickness', ...
        'poreDiameter', 'areaMean'};
    if ~isstruct(profiles) || ~isscalar(profiles) || ...
            ~isequal(fieldnames(profiles)', profileNames)
        throw(MException(errorId, 'descriptor profiles must have the fixed profile order'));
    end
    lines = {'schema_version=1.0'};
    for profileIndex = 1:numel(profileNames)
        profileName = profileNames{profileIndex};
        profile = profiles.(profileName);
        validate_descriptor_result(profile, profileName, ...
            profile.definition_sha256);
        lines{end + 1} = ['profile=', profile.profile]; %#ok<AGROW>
        lines{end + 1} = ['definition_sha256=', profile.definition_sha256]; %#ok<AGROW>
        for descriptorIndex = 1:numel(descriptorNames)
            descriptor = descriptorNames{descriptorIndex};
            lines{end + 1} = sprintf('%s.unit=%s', descriptor, ...
                profile.units.(descriptor)); %#ok<AGROW>
            lines{end + 1} = sprintf('%s.value=%.17g', descriptor, ...
                profile.values.(descriptor)); %#ok<AGROW>
        end
    end
    text = strjoin(lines, newline);
    text = [text, newline];
end
