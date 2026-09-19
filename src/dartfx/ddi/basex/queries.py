"""Query managers and XQuery definitions for DDI-Codebook (DDI-C) and DDI-Lifecycle (DDI-L)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dartfx.ddi.basex.client import BaseXClient


def _parse_xml_element(element: ET.Element) -> dict[str, Any] | str | list[Any]:
    """Recursively converts an XML ElementTree into a clean Python dictionary/list."""
    children = list(element)

    if not children:
        text = (element.text or "").strip()
        if element.attrib:
            data: dict[str, Any] = dict(element.attrib)
            if text:
                data["_value"] = text
            return data
        return text

    result: dict[str, Any] = dict(element.attrib)
    for child in children:
        child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        child_data = _parse_xml_element(child)

        if child_tag in result:
            if not isinstance(result[child_tag], list):
                result[child_tag] = [result[child_tag]]
            result[child_tag].append(child_data)
        else:
            result[child_tag] = child_data

    if element.text and element.text.strip():
        result["_text"] = element.text.strip()

    return result


class BaseDdiQueryManager:
    """Base query manager providing common XQuery execution and parsing routines."""

    def __init__(self, client: BaseXClient) -> None:
        self.client = client

    def execute_raw(
        self,
        xquery: str,
        db_name: str | None = None,
        variables: dict[str, Any] | None = None,
    ) -> str:
        """Executes an XQuery and returns the raw string response."""
        return self.client.query(xquery, db_name=db_name, variables=variables)

    def execute_xml(
        self,
        xquery: str,
        db_name: str | None = None,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Executes an XQuery and returns a parsed dictionary."""
        raw_xml = self.client.query(xquery, db_name=db_name, variables=variables)
        if not raw_xml or not raw_xml.strip():
            return {}
        clean_xml = raw_xml.strip()
        try:
            try:
                root = ET.fromstring(clean_xml)
                tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
                if tag == "result":
                    parsed = _parse_xml_element(root)
                    return parsed if isinstance(parsed, dict) else {"result": parsed}
                else:
                    return {tag: _parse_xml_element(root)}
            except ET.ParseError:
                root = ET.fromstring(f"<result>{clean_xml}</result>")
                parsed = _parse_xml_element(root)
                return parsed if isinstance(parsed, dict) else {"result": parsed}
        except ET.ParseError as exc:
            return {"raw": raw_xml, "error": str(exc)}


class DdiCodebookQueryManager(BaseDdiQueryManager):
    """Specialized query manager for DDI-Codebook (2.1, 2.5, 2.6) XML datasets."""

    def get_study_summary(
        self,
        db_name: str,
        doc_path: str | None = None,
    ) -> dict[str, Any]:
        """Extracts high-level study metadata (citation, title, abstract, files, counts)."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        xquery = f"""
        let $root := {doc_expr}//*:codeBook
        let $stdy := $root/*:stdyDscr
        let $docDscr := $root/*:docDscr
        let $citation := $stdy/*:citation
        let $titlStmt := $citation/*:titlStmt
        let $rspStmt := $citation/*:rspStmt
        let $prodStmt := $citation/*:prodStmt
        let $stdyInfo := $stdy/*:stdyInfo
        let $sumDscr := $stdyInfo/*:sumDscr

        return
        <study_summary>
            <id>{{ ($root/@ID/string(), $titlStmt/*:IDNo[1]/string())[1] }}</id>
            <title>{{ $titlStmt/*:titl[1]/string() }}</title>
            <sub_title>{{ $titlStmt/*:subTitl[1]/string() }}</sub_title>
            <alt_title>{{ $titlStmt/*:altTitl[1]/string() }}</alt_title>
            <abstract>{{ $stdyInfo/*:abstract[1]/string() }}</abstract>
            <universe>{{ $sumDscr/*:universe[1]/string() }}</universe>
            <time_period>
                <start>{{ $sumDscr/*:timePrd/@date/string() }}</start>
                <text>{{ $sumDscr/*:timePrd[1]/string() }}</text>
            </time_period>
            <geography>{{ $sumDscr/*:geogCover[1]/string() }}</geography>
            <producers>
            {{
                for $p in $prodStmt/*:producer
                return <producer>{{ $p/string() }}</producer>
            }}
            </producers>
            <authors>
            {{
                for $a in $rspStmt/*:AuthEnty
                return <author>{{ $a/string() }}</author>
            }}
            </authors>
            <files>
            {{
                for $f in $root/*:fileDscr
                return
                    <cases>{{
                        ($f/*:fileTxt/*:dimensns/*:caseQnty/string(),
                         $f/*:fileTxt/*:fileDimens/*:caseQnty/string())[1]
                    }}</cases>
                    <variables>{{
                        ($f/*:fileTxt/*:dimensns/*:varQnty/string(),
                         $f/*:fileTxt/*:fileDimens/*:varQnty/string())[1]
                    }}</variables>
                </file>
            }}
            </files>
            <total_variables>{{ count($root/*:dataDscr/*:var) }}</total_variables>
            <total_files>{{ count($root/*:fileDscr) }}</total_files>
        </study_summary>
        """
        return self.execute_xml(xquery, db_name=db_name)

    def get_data_dictionary(
        self,
        db_name: str,
        doc_path: str | None = None,
        file_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Extracts complete data dictionary (variables, labels, types, categories, stats)."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        file_filter = f'[@files="{file_id}"]' if file_id else ""
        limit_clause = f"[position() <= {limit}]" if limit else ""

        xquery = f"""
        let $vars := {doc_expr}//*:dataDscr/*:var{file_filter}{limit_clause}
        return
        <variables>
        {{
            for $v in $vars
            return
            <variable id="{{ $v/@ID/string() }}"
                      name="{{ ($v/@name/string(), $v/*:name/string())[1] }}"
                      file="{{ $v/@files/string() }}"
                      type="{{ $v/@type/string() }}">
                <label>{{ $v/*:labl[1]/string() }}</label>
                <question>{{ $v/*:qstn/*:qstnLit[1]/string() }}</question>
                <concept>{{ $v/*:concept[1]/string() }}</concept>
                <format type="{{ $v/*:varFormat/@type/string() }}" schema="{{ $v/*:varFormat/@schema/string() }}"/>
                <categories>
                {{
                    for $cat in $v/*:catgry
                    return
                    <category missing="{{ $cat/@missing/string() }}">
                        <value>{{ $cat/*:catVal[1]/string() }}</value>
                        <label>{{ $cat/*:labl[1]/string() }}</label>
                        <stats>
                        {{
                            for $st in $cat/*:catStat
                            return <stat type="{{ $st/@type/string() }}">{{ $st/string() }}</stat>
                        }}
                        </stats>
                    </category>
                }}
                </categories>
            </variable>
        }}
        </variables>
        """
        res = self.execute_xml(xquery, db_name=db_name)
        vars_data = res.get("variables", {}).get("variable", [])
        if isinstance(vars_data, dict):
            return [vars_data]
        return vars_data if isinstance(vars_data, list) else []

    def get_variables_list(
        self,
        db_name: str,
        doc_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fast extraction of tabular variable list (id, name, label, type, file)."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        xquery = f"""
        let $vars := {doc_expr}//*:dataDscr/*:var
        return
        <variables>
        {{
            for $v in $vars
            return
            <variable id="{{ $v/@ID/string() }}"
                      name="{{ ($v/@name/string(), $v/*:name/string())[1] }}"
                      file="{{ $v/@files/string() }}"
                      type="{{ ($v/@type/string(), $v/*:varFormat/@type/string())[1] }}">
                <label>{{ $v/*:labl[1]/string() }}</label>
                <category_count>{{ count($v/*:catgry) }}</category_count>
            </variable>
        }}
        </variables>
        """
        res = self.execute_xml(xquery, db_name=db_name)
        vars_data = res.get("variables", {}).get("variable", [])
        if isinstance(vars_data, dict):
            return [vars_data]
        return vars_data if isinstance(vars_data, list) else []


class DdiLifecycle3QueryManager(BaseDdiQueryManager):
    """Specialized query manager for DDI-Lifecycle 3.x (3.1, 3.2, 3.3) XML datasets."""

    def get_fragment_inventory(
        self,
        db_name: str,
        doc_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """Counts and groups all fragment types present in the DDI-L 3.x database or document."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        xquery = f"""
        let $doc := {doc_expr}
        let $fragments := $doc//*:Fragment
        return
        <inventory total="{{ count($fragments) }}">
        {{
            if (count($fragments) > 0) then
                for $f in $fragments
                let $type := local-name($f/*[1])
                where string-length($type) > 0
                group by $type
                order by count($f) descending
                return
                <item type="{{ $type }}" count="{{ count($f) }}"/>
            else
                for $el in $doc/*/*
                let $type := local-name($el)
                where string-length($type) > 0
                group by $type
                order by count($el) descending
                return
                <item type="{{ $type }}" count="{{ count($el) }}"/>
        }}
        </inventory>
        """
        res = self.execute_xml(xquery, db_name=db_name)
        inv = res.get("inventory", {})
        items = inv.get("item", [])
        if isinstance(items, dict):
            return [items]
        return items if isinstance(items, list) else []

    def get_study_overview(
        self,
        db_name: str,
        doc_path: str | None = None,
    ) -> dict[str, Any]:
        """Extracts StudyUnit, Citation, Abstract, Universe, and Agency information from DDI-L 3.x."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        xquery = f"""
        let $doc := {doc_expr}
        let $study := ($doc//*:StudyUnit, $doc//*:Fragment/*:StudyUnit)[1]
        let $citation := $study/*:Citation
        let $titlStmt := $citation/*:Title
        let $abstract := $study/*:Abstract/*:Content[1]/string()
        let $universe := $doc//*:Universe/*:HumanReadable[1]/string()

        return
        <lifecycle_study ddi_version="3.x">
            <id>{{ ($study/*:URN/string(), $study/*:ID/string())[1] }}</id>
            <agency>{{ $study/*:Agency/string() }}</agency>
            <version>{{ $study/*:Version/string() }}</version>
            <title>{{ ($titlStmt/*:String[1]/string(), $titlStmt/string())[1] }}</title>
            <abstract>{{ $abstract }}</abstract>
            <universe>{{ $universe }}</universe>
            <total_variables>{{ count($doc//*:Variable | $doc//*:Fragment/*:Variable) }}</total_variables>
            <total_questions>{{
                count($doc//*:QuestionItem | $doc//*:QuestionGrid | $doc//*:Fragment/*:QuestionItem)
            }}</total_questions>
            <total_codelists>{{ count($doc//*:CodeList | $doc//*:Fragment/*:CodeList) }}</total_codelists>
            <total_concepts>{{ count($doc//*:Concept | $doc//*:Fragment/*:Concept) }}</total_concepts>
        </lifecycle_study>
        """
        return self.execute_xml(xquery, db_name=db_name)

    def get_variable_schemes(
        self,
        db_name: str,
        doc_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extracts VariableSchemes and their contained Variables from DDI-L 3.x."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        xquery = f"""
        let $doc := {doc_expr}
        let $schemes := ($doc//*:VariableScheme | $doc//*:Fragment/*:VariableScheme)
        return
        <schemes>
        {{
            for $s in $schemes
            return
            <scheme id="{{ ($s/*:URN/string(), $s/*:ID/string())[1] }}"
                    name="{{ $s/*:VariableSchemeName/*:String[1]/string() }}">
                <variables>
                {{
                    for $v in (
                        $s/*:Variable |
                        $doc//*:Variable[*:VariableSchemeReference/*:ID = $s/*:ID] |
                        $doc//*:Fragment/*:Variable
                    )
                    return
                    <variable id="{{ ($v/*:URN/string(), $v/*:ID/string())[1] }}"
                              name="{{ $v/*:VariableName/*:String[1]/string() }}">
                        <label>{{ $v/*:Label/*:Content/*:String[1]/string() }}</label>
                        <concept_ref>{{ $v/*:ConceptReference/*:ID/string() }}</concept_ref>
                        <question_ref>{{ $v/*:QuestionReference/*:ID/string() }}</question_ref>
                    </variable>
                }}
                </variables>
            </scheme>
        }}
        </schemes>
        """
        res = self.execute_xml(xquery, db_name=db_name)
        schemes_data = res.get("schemes", {}).get("scheme", [])
        if isinstance(schemes_data, dict):
            return [schemes_data]
        return schemes_data if isinstance(schemes_data, list) else []

    def get_codelists(
        self,
        db_name: str,
        doc_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extracts CodeLists with individual codes and category labels from DDI-L 3.x."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        xquery = f"""
        let $doc := {doc_expr}
        let $codelists := ($doc//*:CodeList | $doc//*:Fragment/*:CodeList)
        return
        <codelists>
        {{
            for $cl in $codelists
            return
            <codelist id="{{ ($cl/*:URN/string(), $cl/*:ID/string())[1] }}"
                      name="{{ $cl/*:CodeListName/*:String[1]/string() }}">
                <label>{{ $cl/*:Label/*:Content/*:String[1]/string() }}</label>
                <codes>
                {{
                    for $c in $cl/*:Code
                    return
                    <code value="{{ $c/*:Value/string() }}">
                        <category_ref>{{ $c/*:CategoryReference/*:ID/string() }}</category_ref>
                    </code>
                }}
                </codes>
            </codelist>
        }}
        </codelists>
        """
        res = self.execute_xml(xquery, db_name=db_name)
        cls_data = res.get("codelists", {}).get("codelist", [])
        if isinstance(cls_data, dict):
            return [cls_data]
        return cls_data if isinstance(cls_data, list) else []

    def extract_fragments_xml(
        self,
        db_name: str,
        doc_path: str | None = None,
        resource_types: list[str] | None = None,
    ) -> str:
        """Extracts raw DDI-L 3.x Fragment XML matching resource types."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        filter_clause = ""
        if resource_types:
            type_tests = " or ".join([f"local-name($f/*[1]) = '{t}'" for t in resource_types])
            filter_clause = f"where {type_tests}"

        xquery = f"""
        let $doc := {doc_expr}
        let $frags := $doc//*:Fragment
        return
        <FragmentInstance xmlns="ddi:instance:3_3">
        {{
            for $f in $frags
            {filter_clause}
            return $f
        }}
        </FragmentInstance>
        """
        return self.client.query(xquery, db_name=db_name)

    def get_resources_by_type(
        self,
        db_name: str,
        resource_type: str,
        doc_path: str | None = None,
        start: int = 1,
        limit: int = 20,
        name_regex: str | None = None,
        text_regex: str | None = None,
    ) -> dict[str, Any]:
        """Queries DDI-Lifecycle 3.x resources of a specific type with pagination and regex filtering."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'

        filters = [f"lower-case(local-name($r)) = lower-case('{resource_type}')"]
        if name_regex:
            escaped_name = name_regex.replace("'", "''")
            filters.append(
                f"(matches($r/*[contains(local-name(), 'Name')]/*:String[1]/string(), '{escaped_name}', 'i') or "
                f"matches($r/*:Label/*:Content/*:String[1]/string(), '{escaped_name}', 'i'))"
            )
        if text_regex:
            escaped_text = text_regex.replace("'", "''")
            filters.append(
                f"(matches($r/*:QuestionText/*:LiteralText/*:Text/string(), '{escaped_text}', 'i') or "
                f"matches($r/*:Description/*:Content/*:String[1]/string(), '{escaped_text}', 'i') or "
                f"matches($r/string(), '{escaped_text}', 'i'))"
            )

        where_clause = "where " + " and ".join(filters)

        if limit > 0:
            end_pos = start + limit - 1
            slice_expr = f"$matched[position() = {start} to {end_pos}]"
        else:
            slice_expr = f"$matched[position() >= {start}]"

        xquery = f"""
        let $doc := {doc_expr}
        let $candidates := if (exists($doc//*:Fragment)) then $doc//*:Fragment/* else $doc//*
        let $matched := (
            for $r in $candidates
            {where_clause}
            return $r
        )
        let $total := count($matched)
        let $items := {slice_expr}

        return
        <resource_search ddi_version="3.x"
                         resource_type="{resource_type}"
                         total="{{ $total }}"
                         start="{start}"
                         limit="{limit}">
        {{
            for $r in $items
            return
            <resource type="{{ local-name($r) }}"
                      id="{{ ($r/*:URN/string(), $r/*:ID/string(), $r/@id/string())[1] }}"
                      agency="{{ $r/*:Agency/string() }}"
                      version="{{ $r/*:Version/string() }}">
                <name>{{
                    ($r/*[contains(local-name(), 'Name')]/*:String[1]/string(),
                     $r/*[contains(local-name(), 'Name')]/string())[1]
                }}</name>
                <label>{{
                    ($r/*:Label/*:Content/*:String[1]/string(),
                     $r/*:Label/*:Content/string(),
                     $r/*:Label/string())[1]
                }}</label>
                <description>{{
                    ($r/*:Description/*:Content/*:String[1]/string(),
                     $r/*:Description/string())[1]
                }}</description>
                <question_text>{{
                    ($r/*:QuestionText/*:LiteralText/*:Text/string(),
                     $r/*:QuestionText//*:Text/string())[1]
                }}</question_text>
                <concept_ref>{{ $r/*:ConceptReference/*:ID/string() }}</concept_ref>
                <universe_ref>{{ $r/*:UniverseReference/*:ID/string() }}</universe_ref>
                <response_domain>{{ local-name($r/*[contains(local-name(), 'Domain')][1]) }}</response_domain>
            </resource>
        }}
        </resource_search>
        """
        res = self.execute_xml(xquery, db_name=db_name)
        search_data = res.get("resource_search", {})
        items = search_data.get("resource", [])
        if isinstance(items, dict):
            items = [items]
        elif not isinstance(items, list):
            items = []

        total_count = int(search_data.get("total", len(items)))

        return {
            "ddi_version": "3.x",
            "resource_type": resource_type,
            "total": total_count,
            "start": start,
            "limit": limit,
            "count": len(items),
            "items": items,
        }

    def get_class_reference_graph(
        self,
        db_name: str,
        doc_path: str | None = None,
        target_class: str | None = None,
        source_class: str | None = None,
        min_count: int = 0,
    ) -> dict[str, Any]:
        """Analyzes how resource classes reference each other across DDI-L 3.x XML fragments."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'

        target_filter = f"where $tgtType = '{target_class}'" if target_class else ""
        source_filter = f"where $srcType = '{source_class}'" if source_class else ""

        xquery = f"""
        declare namespace i  = "ddi:instance:3_3";
        declare namespace r  = "ddi:reusable:3_3";

        let $doc := {doc_expr}
        let $fragments := if (exists($doc//*:Fragment)) then $doc//*:Fragment else $doc/*/*

        let $resources := (
            for $f in $fragments
            let $elem := if (local-name($f) = "Fragment") then $f/*[1] else $f
            let $type := local-name($elem)
            let $agency := string($elem/*:Agency)
            let $id := string($elem/*:ID)
            let $ver := string($elem/*:Version)
            let $urn := string($elem/*:URN)
            where string-length($type) > 0
            return <res type="{{ $type }}" agency="{{ $agency }}" id="{{ $id }}" ver="{{ $ver }}" urn="{{ $urn }}"/>
        )

        let $refs := (
            for $f in $fragments
            let $sourceElem := if (local-name($f) = "Fragment") then $f/*[1] else $f
            let $srcType := local-name($sourceElem)
            {source_filter}
            for $ref in $sourceElem//*[
                ends-with(local-name(), 'Reference') or
                ends-with(local-name(), 'Ref') or
                *:TypeOfObject
            ]
            let $refElem := local-name($ref)
            let $refAgency := string($ref/*:Agency)
            let $refId := string($ref/*:ID)
            let $refVer := string($ref/*:Version)
            let $refUrn := string($ref/*:URN)
            let $typeOfObj := string($ref/*:TypeOfObject)

            let $tgtType := (
                if (string-length($typeOfObj) > 0) then $typeOfObj
                else if (string-length($refUrn) > 0 and exists($resources[@urn = $refUrn])) then
                    string(($resources[@urn = $refUrn])[1]/@type)
                else if (string-length($refId) > 0 and exists($resources[@agency = $refAgency and @id = $refId])) then
                    string(($resources[@agency = $refAgency and @id = $refId])[1]/@type)
                else if (ends-with($refElem, 'Reference')) then
                    substring($refElem, 1, string-length($refElem) - 9)
                else if (ends-with($refElem, 'Ref')) then
                    substring($refElem, 1, string-length($refElem) - 3)
                else $refElem
            )[1]
            {target_filter}
            where string-length($tgtType) > 0
            return <edge src="{{ $srcType }}" tgt="{{ $tgtType }}" ref="{{ $refElem }}"/>
        )

        return
        <reference_graph total_references="{{ count($refs) }}">
        {{
            for $e in $refs
            let $s := string($e/@src)
            let $t := string($e/@tgt)
            let $r := string($e/@ref)
            let $cnt := count($e)
            group by $s, $t, $r
            where $cnt >= {min_count}
            order by $cnt descending
            return
            <path source="{{ $s }}" target="{{ $t }}" reference_element="{{ $r }}" count="{{ $cnt }}"/>
        }}
        </reference_graph>
        """
        return self.execute_xml(xquery, db_name=db_name)


class DdiLifecycle4QueryManager(BaseDdiQueryManager):
    """Specialized query manager for DDI 4.0 RC1 XML / ItemContainer datasets."""

    def get_item_inventory(
        self,
        db_name: str,
        doc_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """Counts and groups all item types in the DDI 4.0 database or document."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        xquery = f"""
        let $doc := {doc_expr}
        let $items := if (exists($doc//*:ItemContainer)) then $doc//*:ItemContainer/* else $doc/*/*
        return
        <inventory total="{{ count($items) }}">
        {{
            for $item in $items
            let $type := local-name($item)
            where string-length($type) > 0 and $type != 'ItemContainer'
            group by $type
            order by count($item) descending
            return
            <item type="{{ $type }}" count="{{ count($item) }}"/>
        }}
        </inventory>
        """
        res = self.execute_xml(xquery, db_name=db_name)
        inv = res.get("inventory", {})
        items = inv.get("item", [])
        if isinstance(items, dict):
            return [items]
        return items if isinstance(items, list) else []

    def get_study_overview(
        self,
        db_name: str,
        doc_path: str | None = None,
    ) -> dict[str, Any]:
        """Extracts StudyUnit, Citation, Abstract, Universe, and Agency information from DDI 4.0."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        xquery = f"""
        let $doc := {doc_expr}
        let $study := ($doc//*:StudyUnit)[1]
        let $citation := $study/*:Citation
        let $title := (
            $citation/*:Title/*:String[1]/string(),
            $citation/*:Title/string(),
            $study/*:StudyUnitName/string(),
            $study/*:Name/string()
        )[1]
        let $abstract := ($study/*:Abstract/*:Content/*:String[1]/string(), $study/*:Abstract/string())[1]
        let $universe := ($doc//*:Universe/*:HumanReadable/*:String[1]/string(), $doc//*:Universe/string())[1]

        return
        <lifecycle_study ddi_version="4.0">
            <id>{{ ($study/*:URN/string(), $study/*:ID/string())[1] }}</id>
            <agency>{{ $study/*:Agency/string() }}</agency>
            <version>{{ $study/*:Version/string() }}</version>
            <title>{{ $title }}</title>
            <abstract>{{ $abstract }}</abstract>
            <universe>{{ $universe }}</universe>
            <total_variables>{{ count($doc//*:Variable) }}</total_variables>
            <total_questions>{{ count($doc//*:QuestionItem | $doc//*:QuestionGrid) }}</total_questions>
            <total_codelists>{{ count($doc//*:CodeList) }}</total_codelists>
            <total_concepts>{{ count($doc//*:Concept) }}</total_concepts>
        </lifecycle_study>
        """
        return self.execute_xml(xquery, db_name=db_name)

    def get_codelists(
        self,
        db_name: str,
        doc_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extracts CodeLists with individual codes and category references from DDI 4.0."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        xquery = f"""
        let $doc := {doc_expr}
        let $codelists := $doc//*:CodeList
        return
        <codelists>
        {{
            for $cl in $codelists
            return
            <codelist id="{{ ($cl/*:URN/string(), $cl/*:ID/string())[1] }}"
                      name="{{ ($cl/*:CodeListName/string(), $cl/*:Name/string())[1] }}">
                <label>{{ ($cl/*:DisplayLabel/string(), $cl/*:Label/string())[1] }}</label>
                <codes>
                {{
                    for $c in $cl/*:Code
                    return
                    <code value="{{ $c/*:Value/string() }}">
                        <category_ref>{{
                            ($c/*:CategoryReference/*:ID/string(),
                             $c/*:CategoryReference/*:URN/string())[1]
                        }}</category_ref>
                    </code>
                }}
                </codes>
            </codelist>
        }}
        </codelists>
        """
        res = self.execute_xml(xquery, db_name=db_name)
        cls_data = res.get("codelists", {}).get("codelist", [])
        if isinstance(cls_data, dict):
            return [cls_data]
        return cls_data if isinstance(cls_data, list) else []

    def extract_items_xml(
        self,
        db_name: str,
        doc_path: str | None = None,
        resource_types: list[str] | None = None,
    ) -> str:
        """Extracts raw DDI 4.0 ItemContainer XML matching resource types."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'
        filter_clause = ""
        if resource_types:
            type_tests = " or ".join([f"local-name($item) = '{t}'" for t in resource_types])
            filter_clause = f"where {type_tests}"

        xquery = f"""
        let $doc := {doc_expr}
        let $items := if (exists($doc//*:ItemContainer)) then $doc//*:ItemContainer/* else $doc/*/*
        return
        <ItemContainer xmlns="https://ddialliance.org/ddi">
        {{
            for $item in $items
            {filter_clause}
            return $item
        }}
        </ItemContainer>
        """
        return self.client.query(xquery, db_name=db_name)

    def get_resources_by_type(
        self,
        db_name: str,
        resource_type: str,
        doc_path: str | None = None,
        start: int = 1,
        limit: int = 20,
        name_regex: str | None = None,
        text_regex: str | None = None,
    ) -> dict[str, Any]:
        """Queries DDI 4.0 resources of a specific type with pagination and regex filtering."""
        doc_expr = f'doc("{db_name}/{doc_path}")' if doc_path else f'collection("{db_name}")'

        filters = [f"lower-case(local-name($r)) = lower-case('{resource_type}')"]
        if name_regex:
            escaped_name = name_regex.replace("'", "''")
            filters.append(
                f"(matches($r/*[contains(local-name(), 'Name')]/string(), '{escaped_name}', 'i') or "
                f"matches($r/*:DisplayLabel/string(), '{escaped_name}', 'i') or "
                f"matches($r/*:Label/string(), '{escaped_name}', 'i'))"
            )
        if text_regex:
            escaped_text = text_regex.replace("'", "''")
            filters.append(
                f"(matches($r/*:QuestionText/*:Text/string(), '{escaped_text}', 'i') or "
                f"matches($r/*:QuestionText/string(), '{escaped_text}', 'i') or "
                f"matches($r/*:Description/string(), '{escaped_text}', 'i') or "
                f"matches($r/string(), '{escaped_text}', 'i'))"
            )

        where_clause = "where " + " and ".join(filters)

        if limit > 0:
            end_pos = start + limit - 1
            slice_expr = f"$matched[position() = {start} to {end_pos}]"
        else:
            slice_expr = f"$matched[position() >= {start}]"

        xquery = f"""
        let $doc := {doc_expr}
        let $candidates := if (exists($doc//*:ItemContainer)) then $doc//*:ItemContainer/* else $doc//*
        let $matched := (
            for $r in $candidates
            {where_clause}
            return $r
        )
        let $total := count($matched)
        let $items := {slice_expr}

        return
        <resource_search ddi_version="4.0"
                         resource_type="{resource_type}"
                         total="{{ $total }}"
                         start="{start}"
                         limit="{limit}">
        {{
            for $r in $items
            return
            <resource type="{{ local-name($r) }}"
                      id="{{ ($r/*:URN/string(), $r/*:ID/string(), $r/@id/string())[1] }}"
                      agency="{{ $r/*:Agency/string() }}"
                      version="{{ $r/*:Version/string() }}">
                <name>{{
                    ($r/*[contains(local-name(), 'Name')]/*:String[1]/string(),
                     $r/*[contains(local-name(), 'Name')]/string())[1]
                }}</name>
                <label>{{
                    ($r/*:DisplayLabel/*:Content/*:String[1]/string(),
                     $r/*:DisplayLabel/string(),
                     $r/*:Label/*:Content/*:String[1]/string(),
                     $r/*:Label/string())[1]
                }}</label>
                <description>{{
                    ($r/*:Description/*:Content/*:String[1]/string(),
                     $r/*:Description/string())[1]
                }}</description>
                <question_text>{{
                    ($r/*:QuestionText/*:Text/string(),
                     $r/*:QuestionText/*:LiteralText/*:Text/string(),
                     $r/*:QuestionText//*:Text/string())[1]
                }}</question_text>
                <concept_ref>{{
                    ($r/*:ConceptReference/*:ID/string(),
                     $r/*:ConceptReference/*:URN/string())[1]
                }}</concept_ref>
                <universe_ref>{{
                    ($r/*:UniverseReference/*:ID/string(),
                     $r/*:UniverseReference/*:URN/string())[1]
                }}</universe_ref>
                <response_domain>{{ local-name($r/*[contains(local-name(), 'Domain')][1]) }}</response_domain>
            </resource>
        }}
        </resource_search>
        """
        res = self.execute_xml(xquery, db_name=db_name)
        search_data = res.get("resource_search", {})
        items = search_data.get("resource", [])
        if isinstance(items, dict):
            items = [items]
        elif not isinstance(items, list):
            items = []

        total_count = int(search_data.get("total", len(items)))

        return {
            "ddi_version": "4.0",
            "resource_type": resource_type,
            "total": total_count,
            "start": start,
            "limit": limit,
            "count": len(items),
            "items": items,
        }


# Backwards compatibility alias
DdiLifecycleQueryManager = DdiLifecycle3QueryManager
